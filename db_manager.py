"""
SQLite persistence layer for resumability and P95/throughput benchmarking.

Schema stores per-request results; indexes enable fast resume checks
and aggregation by endpoint.
"""

import sqlite3
from pathlib import Path
from typing import Literal

# Table and column names
TABLE = "extract_runs"
COL_FILE = "file_name"
COL_ENDPOINT = "endpoint_used"
COL_STATUS = "status"
COL_LATENCY_MS = "latency_ms"
COL_RESPONSE_BODY = "response_body"
COL_ERROR_TYPE = "error_type"
COL_SERVER_PROCESSING_MS = "server_processing_ms"
COL_NETWORK_OVERHEAD_MS = "network_overhead_ms"
COL_TS = "created_at"

EndpointMode = Literal["url", "upload"]
STATUS_SUCCESS = "success"
STATUS_FAILURE = "failure"


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    """Return a connection to the SQLite DB; creates file if needed. Uses WAL mode for concurrent writes."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """
    Create the extract_runs table and indexes for fast resume and reporting.
    """
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {COL_FILE} TEXT NOT NULL,
            {COL_ENDPOINT} TEXT NOT NULL,
            {COL_STATUS} TEXT NOT NULL,
            {COL_LATENCY_MS} REAL,
            {COL_SERVER_PROCESSING_MS} REAL,
            {COL_NETWORK_OVERHEAD_MS} REAL,
            {COL_RESPONSE_BODY} TEXT,
            {COL_ERROR_TYPE} TEXT,
            {COL_TS} TEXT DEFAULT (datetime('now'))
        )
        """
    )
    try:
        conn.execute(f"ALTER TABLE {TABLE} ADD COLUMN {COL_ERROR_TYPE} TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute(f"ALTER TABLE {TABLE} ADD COLUMN {COL_SERVER_PROCESSING_MS} REAL")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute(f"ALTER TABLE {TABLE} ADD COLUMN {COL_NETWORK_OVERHEAD_MS} REAL")
    except sqlite3.OperationalError:
        pass

    # Fast resume: skip if (file_name, endpoint_used) already success
    conn.execute(
        f"""
        CREATE INDEX IF NOT EXISTS idx_resume
        ON {TABLE} ({COL_FILE}, {COL_ENDPOINT})
        WHERE {COL_STATUS} = 'success'
        """
    )
    # Aggregation by endpoint for P95 and failure rate
    conn.execute(
        f"CREATE INDEX IF NOT EXISTS idx_endpoint ON {TABLE} ({COL_ENDPOINT})"
    )
    conn.execute(
        f"CREATE INDEX IF NOT EXISTS idx_created ON {TABLE} ({COL_TS})"
    )
    conn.commit()


def is_already_success(conn: sqlite3.Connection, file_name: str, endpoint: str) -> bool:
    """Return True if this (file_name, endpoint) already has a success record."""
    cur = conn.execute(
        f"SELECT 1 FROM {TABLE} WHERE {COL_FILE} = ? AND {COL_ENDPOINT} = ? AND {COL_STATUS} = ? LIMIT 1",
        (file_name, endpoint, STATUS_SUCCESS),
    )
    return cur.fetchone() is not None


def insert_result(
    conn: sqlite3.Connection,
    file_name: str,
    endpoint_used: str,
    status: str,
    latency_ms: float | None,
    server_processing_ms: float | None,
    network_overhead_ms: float | None,
    response_body: str,
    error_type: str | None = None,
) -> None:
    """Insert one run result."""
    conn.execute(
        f"""
        INSERT INTO {TABLE} ({COL_FILE}, {COL_ENDPOINT}, {COL_STATUS}, {COL_LATENCY_MS}, {COL_SERVER_PROCESSING_MS}, {COL_NETWORK_OVERHEAD_MS}, {COL_RESPONSE_BODY}, {COL_ERROR_TYPE})
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (file_name, endpoint_used, status, latency_ms, server_processing_ms, network_overhead_ms, response_body, error_type),
    )
    conn.commit()


def get_runs_by_endpoint(
    conn: sqlite3.Connection, endpoint: str
) -> list[sqlite3.Row]:
    """Return all rows for the given endpoint (for P95 and failure count)."""
    cur = conn.execute(
        f"SELECT * FROM {TABLE} WHERE {COL_ENDPOINT} = ? ORDER BY {COL_TS}",
        (endpoint,),
    )
    return cur.fetchall()


def get_all_runs(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Return all rows (for reporter)."""
    cur = conn.execute(f"SELECT * FROM {TABLE} ORDER BY {COL_TS}")
    return cur.fetchall()


def clean_db(db_path: str | Path, vacuum: bool = True) -> int:
    """
    Delete all rows from extract_runs. Optionally run VACUUM to reclaim space.
    Returns the number of rows deleted.
    """
    conn = get_connection(db_path)
    cur = conn.execute(f"SELECT COUNT(*) FROM {TABLE}")
    count = cur.fetchone()[0]
    conn.execute(f"DELETE FROM {TABLE}")
    conn.commit()
    if vacuum:
        conn.execute("VACUUM")
    conn.close()
    return count


def get_slowest_runs(conn: sqlite3.Connection, limit: int = 5) -> list[sqlite3.Row]:
    """Return top N slowest successful runs."""
    cur = conn.execute(
        f"""
        SELECT {COL_FILE}, {COL_ENDPOINT}, {COL_LATENCY_MS}
        FROM {TABLE}
        WHERE {COL_STATUS} = ? AND {COL_LATENCY_MS} IS NOT NULL
        ORDER BY {COL_LATENCY_MS} DESC
        LIMIT ?
        """,
        (STATUS_SUCCESS, limit),
    )
    return cur.fetchall()


def get_failure_counts_by_type(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Return failure counts grouped by error_type."""
    cur = conn.execute(
        f"""
        SELECT {COL_ERROR_TYPE}, COUNT(*) as count
        FROM {TABLE}
        WHERE {COL_STATUS} = ?
        GROUP BY {COL_ERROR_TYPE}
        ORDER BY count DESC
        """,
        (STATUS_FAILURE,),
    )
    return cur.fetchall()
