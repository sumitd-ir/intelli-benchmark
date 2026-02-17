"""
Orchestrator: test loop, concurrency (semaphore), dual-path mode, resume, report.

Usage:
  python main.py --concurrency 10 --mode dual
  python main.py -c 5 -m url --report ./Executive_Summary.md
  python main.py --report-only --db ./intelli_extract.db --report ./Executive_Summary.md
  python main.py --clean-db --db ./intelli_extract.db
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from tqdm.asyncio import tqdm # Use tqdm.asyncio if preferred or just standard tqdm with as_completed

# Load env vars from .env file if present
load_dotenv()

from api_client import EndpointMode, IntelliExtractClient
from auth import HeaderFactory
from db_manager import (
    STATUS_FAILURE,
    STATUS_SUCCESS,
    clean_db,
    get_connection,
    init_schema,
    insert_result,
    is_already_success,
)
from reporter import generate_report
from reporter import generate_report
from s3_manager import DEFAULT_BUCKET, DEFAULT_ALLOWED_EXTENSIONS, get_presigned_urls_for_prefix, sync_prefix_to_local

RUN_MODE = Literal["url", "upload", "dual"]


def parse_args():
    p = argparse.ArgumentParser(description="Intelli-Benchmark: Dual-Path Test Runner for intelliExtract API")
    p.add_argument("--concurrency", "-c", type=int, default=10, help="Max concurrent requests")
    p.add_argument("--rate-limit", "-r", type=int, default=0, help="Max requests per minute (0 = no cap)")
    p.add_argument("--mode", "-m", choices=("url", "upload", "dual"), default="dual", help="url, upload, or 50/50 dual")
    p.add_argument("--db", default="./intelli_extract.db", help="SQLite DB path")
    p.add_argument("--report", default="./Executive_Summary.md", help="Output Markdown report path")
    p.add_argument("--bucket", default=DEFAULT_BUCKET, help="S3 bucket for file discovery")
    p.add_argument("--prefix", default="", help="S3 key prefix")
    p.add_argument("--local-dir", default="./staging", help="Local directory for syncing S3 files")
    p.add_argument("--limit", type=int, help="Limit number of files to process")
    p.add_argument(
        "--formats",
        default=",".join(DEFAULT_ALLOWED_EXTENSIONS),
        help="Comma-separated file extensions to consider from S3 (e.g. .xlsx,.csv). Default: .xlsx,.xls,.csv,.ods. Use empty string to allow all.",
    )
    p.add_argument("--report-only", action="store_true", help="Only generate report from existing DB; no test run")
    p.add_argument("--clean-db", action="store_true", help="Clear all rows from the DB and exit (use --db to set path)")
    return p.parse_args()


async def run_one(
    client: IntelliExtractClient,
    semaphore: asyncio.Semaphore,
    mode: EndpointMode,
    file_name: str,
    url: str | None,
    file_path: Path | None,
    db_path: str,
) -> bool:
    """Execute one extract (url or upload), record in DB. Returns True if success."""
    async with semaphore:
        result = await client.extract(mode, url=url, file_path=file_path)
    conn = get_connection(db_path)
    status = STATUS_SUCCESS if result.success else STATUS_FAILURE
    insert_result(
        conn,
        file_name=file_name,
        endpoint_used=mode,
        status=status,
        latency_ms=result.latency_ms if result.success else None,
        response_body=(result.response_body or "")[:65535],  # cap for SQLite
        error_type=result.error_type,
    )
    conn.close()
    return result.success





def _sync_phase(args, allowed_extensions) -> dict[str, Path]:
    """Phase 1: Sync S3 files to local staging if needed."""
    local_files_map: dict[str, Path] = {}
    try:
        if args.mode in ("upload", "dual"):
            synced_paths = sync_prefix_to_local(
                bucket=args.bucket,
                prefix=args.prefix,
                local_dir=args.local_dir,
                allowed_extensions=allowed_extensions,
                limit=args.limit,
            )
            for p in synced_paths:
                local_files_map[p.name] = p
    except Exception as e:
        print(f"Sync failed: {e}")
    return local_files_map


def _discovery_phase(args, allowed_extensions) -> list[tuple[str, str]]:
    """Phase 2: Discover files/URLs from S3."""
    try:
        return get_presigned_urls_for_prefix(
            bucket=args.bucket,
            prefix=args.prefix,
            allowed_extensions=allowed_extensions if allowed_extensions else None,
            limit=args.limit,
        )
    except Exception as e:
        print(f"S3 discovery failed: {e}. Run with --mode upload and local files, or set AWS credentials.")
        return []


def _create_task_for_item(args, file_name, presigned_url, local_files_map):
    """Create task tuple for a single item."""
    tasks = []
    if args.mode in ("url", "dual"):
        tasks.append(("url", file_name, presigned_url, None))
        
    if args.mode in ("upload", "dual"):
        local_path = local_files_map.get(file_name)
        if local_path and local_path.exists():
            tasks.append(("upload", file_name, None, local_path))
        elif args.mode == "upload":
             print(f"Warning: Local file for {file_name} not found in {args.local_dir}. Skipping upload test.")
    return tasks


def _build_task_list(args, url_tuples, local_files_map) -> list[tuple[EndpointMode, str, str | None, Path | None]]:
    """Phase 3: Build list of tasks based on mode and discovered files."""
    tasks: list[tuple[EndpointMode, str, str | None, Path | None]] = []
    for key, presigned_url in url_tuples:
        file_name = Path(key).name or key
        new_tasks = _create_task_for_item(args, file_name, presigned_url, local_files_map)
        tasks.extend(new_tasks)
    return tasks


def _filter_resumable_tasks(args, tasks) -> list[tuple[EndpointMode, str, str | None, Path | None]]:
    """Phase 4: Filter out tasks that are already successful in DB."""
    to_run: list[tuple[EndpointMode, str, str | None, Path | None]] = []
    conn = get_connection(args.db)
    for mode, file_name, url, path in tasks:
        if is_already_success(conn, file_name, mode):
            continue
        to_run.append((mode, file_name, url, path))
    conn.close()
    return to_run


async def _execute_tasks(args, client, semaphore, to_run) -> float:
    """Phase 5: Execute tasks with progress bar."""
    total = len(to_run)
    start = time.perf_counter()
    
    coros = [
        run_one(
            client,
            semaphore,
            mode,
            file_name,
            url,
            path,
            args.db,
        )
        for mode, file_name, url, path in to_run
    ]

    success_count = 0
    fail_count = 0

    for f in tqdm(asyncio.as_completed(coros), total=total, desc="Running tests", unit="req"):
        is_success = await f
        if is_success:
            success_count += 1
        else:
            fail_count += 1

    elapsed_sec = time.perf_counter() - start
    print(f"Completed {len(to_run)} tasks in {elapsed_sec:.2f}s | Success: {success_count} | Fail: {fail_count}")
    return elapsed_sec


async def orchestrator_main(args) -> None:
    header_factory = HeaderFactory()
    if not header_factory.is_configured():
        print("Warning: INTELLI_ACCESS_KEY / INTELLI_SIGNATURE / INTELLI_SECRET_MESSAGE not set.")

    conn = get_connection(args.db)
    init_schema(conn)
    conn.close()

    allowed_extensions = None
    if getattr(args, "formats", ""):
        allowed_extensions = [e.strip() for e in args.formats.split(",") if e.strip()]

    # Phases 1-4: Setup and Planning
    local_files_map = _sync_phase(args, allowed_extensions)
    url_tuples = _discovery_phase(args, allowed_extensions)
    tasks = _build_task_list(args, url_tuples, local_files_map)
    to_run = _filter_resumable_tasks(args, tasks)

    elapsed_sec: float | None = None
    if not to_run:
        if not tasks:
            print("No work to do: no files from S3 (discovery failed or bucket empty). Set AWS credentials and ensure the bucket is accessible.")
        else:
            print("No work to do (all tasks already succeeded in DB).")
    else:
        # Phase 5: Execution
        client = IntelliExtractClient(header_factory=header_factory)
        semaphore = asyncio.Semaphore(args.concurrency)
        elapsed_sec = await _execute_tasks(args, client, semaphore, to_run)

    generate_report(
        args.db,
        args.report,
        run_mode=args.mode,
        concurrency=args.concurrency,
        run_duration_sec=elapsed_sec,
    )
    print(f"Report written to {args.report}")


def main():
    args = parse_args()
    if getattr(args, "clean_db", False):
        deleted = clean_db(args.db)
        print(f"Cleaned DB: {deleted} row(s) removed from {args.db}")
        return
    if args.report_only:
        generate_report(
            args.db,
            args.report,
            run_mode=args.mode,
            concurrency=args.concurrency,
            run_duration_sec=None,
        )
        print(f"Report written to {args.report}")
        return
    try:
        asyncio.run(orchestrator_main(args))
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nInterrupted. Generating report from current DB state...")
        generate_report(
            args.db,
            args.report,
            run_mode=args.mode,
            concurrency=args.concurrency,
            run_duration_sec=None,
        )
        print(f"Report written to {args.report}")
        sys.exit(130)


if __name__ == "__main__":
    main()
