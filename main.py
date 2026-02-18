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
from s3_manager import DEFAULT_BUCKET, DEFAULT_ALLOWED_EXTENSIONS, get_presigned_urls_for_prefix, sync_prefix_to_local
import cli_ui

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
            with cli_ui.console.status("[bold green]Syncing files from S3..."):
                synced_paths = sync_prefix_to_local(
                    bucket=args.bucket,
                    prefix=args.prefix,
                    local_dir=args.local_dir,
                    allowed_extensions=allowed_extensions,
                    limit=args.limit,
                )
            for p in synced_paths:
                local_files_map[p.name] = p
            cli_ui.print_success(f"Synced {len(synced_paths)} files to {args.local_dir}")
    except Exception as e:
        cli_ui.print_error(f"Sync failed: {e}")
    return local_files_map


def _discovery_phase(args, allowed_extensions) -> list[tuple[str, str]]:
    """Phase 2: Discover files/URLs from S3."""
    try:
        with cli_ui.console.status("[bold green]Discovering S3 objects..."):
            urls = get_presigned_urls_for_prefix(
                bucket=args.bucket,
                prefix=args.prefix,
                allowed_extensions=allowed_extensions if allowed_extensions else None,
                limit=args.limit,
            )
        cli_ui.print_info(f"Discovered {len(urls)} objects in S3")
        return urls
    except Exception as e:
        cli_ui.print_error(f"S3 discovery failed: {e}. Run with --mode upload and local files, or set AWS credentials.")
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
             cli_ui.print_warning(f"Local file for {file_name} not found in {args.local_dir}. Skipping upload test.")
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
    
    skipped = len(tasks) - len(to_run)
    if skipped > 0:
        cli_ui.print_info(f"Skipping {skipped} tasks already completed successfully.")
    
    return to_run


async def _execute_tasks(args, client, semaphore, to_run) -> tuple[float, int, int]:
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

    with cli_ui.create_progress() as progress:
        task_id = progress.add_task("[cyan]Running tests...", total=total)
        
        for f in asyncio.as_completed(coros):
            is_success = await f
            if is_success:
                success_count += 1
            else:
                fail_count += 1
            progress.advance(task_id)

    elapsed_sec = time.perf_counter() - start
    return elapsed_sec, success_count, fail_count


async def orchestrator_main(args) -> None:
    cli_ui.print_banner()
    cli_ui.print_header("Intelli-Benchmark", "Dual-Path Test Runner for intelliExtract API")

    header_factory = HeaderFactory()
    if not header_factory.is_configured():
        cli_ui.print_warning("INTELLI_ACCESS_KEY / INTELLI_SIGNATURE / INTELLI_SECRET_MESSAGE not set.")

    conn = get_connection(args.db)
    init_schema(conn)
    conn.close()

    allowed_extensions = None
    if getattr(args, "formats", ""):
        allowed_extensions = [e.strip() for e in args.formats.split(",") if e.strip()]

    # Phases 1-4: Setup and Planning
    cli_ui.print_step("Phase 1: S3 Sync")
    local_files_map = _sync_phase(args, allowed_extensions)
    
    cli_ui.print_step("Phase 2: Discovery")
    url_tuples = _discovery_phase(args, allowed_extensions)
    
    cli_ui.print_step("Phase 3: Task Compilation")
    tasks = _build_task_list(args, url_tuples, local_files_map)
    cli_ui.print_info(f"Total potential tasks: {len(tasks)}")
    
    to_run = _filter_resumable_tasks(args, tasks)

    elapsed_sec: float | None = None
    success_count = 0
    fail_count = 0

    if not to_run:
        if not tasks:
            cli_ui.print_warning("No work to do: no files from S3 (discovery failed or bucket empty).")
        else:
            cli_ui.print_success("All tasks already completed successfully.")
            # Still valid to generate a report, maybe? 
    else:
        # Phase 5: Execution
        cli_ui.print_step(f"Phase 4: Execution ({len(to_run)} tasks)")
        client = IntelliExtractClient(header_factory=header_factory)
        semaphore = asyncio.Semaphore(args.concurrency)
        elapsed_sec, success_count, fail_count = await _execute_tasks(args, client, semaphore, to_run)

    cli_ui.print_step("Phase 5: Reporting")
    generate_report(
        args.db,
        args.report,
        run_mode=args.mode,
        concurrency=args.concurrency,
        run_duration_sec=elapsed_sec,
    )
    
    if elapsed_sec is not None:
         cli_ui.print_summary_table(
            duration_sec=elapsed_sec,
            success_count=success_count,
            fail_count=fail_count,
            concurrency=args.concurrency,
            mode=args.mode,
            report_path=args.report
        )
    else:
        cli_ui.print_success(f"Report updated at {args.report}")


def main():
    args = parse_args()
    if getattr(args, "clean_db", False):
        deleted = clean_db(args.db)
        cli_ui.console.print(f"[bold green]Cleaned DB:[/bold green] {deleted} row(s) removed from {args.db}")
        return
    if args.report_only:
        cli_ui.print_header("Intelli-Benchmark", "Report Generation Only")
        generate_report(
            args.db,
            args.report,
            run_mode=args.mode,
            concurrency=args.concurrency,
            run_duration_sec=None,
        )
        cli_ui.print_success(f"Report written to {args.report}")
        return
    try:
        asyncio.run(orchestrator_main(args))
    except (KeyboardInterrupt, asyncio.CancelledError):
        cli_ui.print_warning("\nInterrupted. Generating report from current DB state...")
        generate_report(
            args.db,
            args.report,
            run_mode=args.mode,
            concurrency=args.concurrency,
            run_duration_sec=None,
        )
        cli_ui.print_success(f"Interrupted report written to {args.report}")
        sys.exit(130)


if __name__ == "__main__":
    main()
