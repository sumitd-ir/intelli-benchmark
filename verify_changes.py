
import sqlite3
from pathlib import Path
from db_manager import init_schema, insert_result, STATUS_FAILURE, STATUS_SUCCESS
from reporter import generate_report

DB_PATH = "verify_test.db"
REPORT_PATH = "verify_report.md"

def setup_db():
    if Path(DB_PATH).exists():
        Path(DB_PATH).unlink()
    
    conn = sqlite3.connect(DB_PATH)
    # create table
    init_schema(conn)
    
    # insert success
    insert_result(conn, "file1.xlsx", "url", STATUS_SUCCESS, 100.0, "ok")
    insert_result(conn, "file2.xlsx", "url", STATUS_SUCCESS, 200.0, "ok")
    insert_result(conn, "file3.xlsx", "upload", STATUS_SUCCESS, 150.0, "ok")
    
    # insert failures with error types
    insert_result(conn, "fail1.xlsx", "url", STATUS_FAILURE, None, "", error_type="Timeout")
    insert_result(conn, "fail2.xlsx", "url", STATUS_FAILURE, None, "", error_type="ClientError")
    insert_result(conn, "fail3.xlsx", "upload", STATUS_FAILURE, None, "", error_type="Timeout")
    insert_result(conn, "fail4.xlsx", "upload", STATUS_FAILURE, None, "", error_type="Timeout")
    insert_result(conn, "fail5.xlsx", "url", STATUS_FAILURE, None, "", error_type="ServerError")
    
    # insert slowest
    insert_result(conn, "slow1.xlsx", "upload", STATUS_SUCCESS, 5000.0, "ok")
    
    conn.close()
    print(f"DB created at {DB_PATH}")

def run_report():
    generate_report(DB_PATH, REPORT_PATH, run_mode="dual", concurrency=10)
    print(f"Report generated at {REPORT_PATH}")
    
    content = Path(REPORT_PATH).read_text(encoding="utf-8")
    print("\n--- Report Snippet ---")
    if "## Failure Breakdown" in content:
        print("SUCCESS: Failure Breakdown section found.")
    else:
        print("FAILURE: Failure Breakdown section NOT found.")
        
    if "## Top 5 Slowest Files" in content:
        print("SUCCESS: Top 5 Slowest Files section found.")
    else:
        print("FAILURE: Top 5 Slowest Files section NOT found.")

    if "| Timeout | 3 |" in content:
        print("SUCCESS: Timeout count correct (3).")
    else:
        print("FAILURE: Timeout count incorrect.")

if __name__ == "__main__":
    setup_db()
    run_report()
