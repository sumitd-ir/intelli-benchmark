"""
Markdown report generator: reads DB, computes P95/P99/FPM, produces Executive Summary.

Uses formal LaTeX notation for latency and throughput. Optionally uses an LLM
to identify anomalies and recommend which endpoint is more stable or has better latency.
"""

import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from db_manager import (
    COL_ENDPOINT,
    COL_FILE,
    COL_LATENCY_MS,
    COL_RESPONSE_BODY,
    COL_STATUS,
    COL_STATUS,
    COL_TS,
    STATUS_SUCCESS,
    get_connection,
    get_runs_by_endpoint,
    get_all_runs,
    get_slowest_runs,
    get_failure_counts_by_type,
)

EndpointMode = Literal["url", "upload"]


def _percentile(latencies: list[float], p: float) -> float | None:
    """Return p-th percentile (0..1) of latencies in ms, or None if empty."""
    if not latencies:
        return None
    sorted_lat = sorted(latencies)
    idx = max(0, int(len(sorted_lat) * p) - 1)
    return sorted_lat[idx]


def p95_latency_ms(latencies: list[float]) -> float | None:
    """Return 95th percentile of latencies in ms, or None if empty."""
    return _percentile(latencies, 0.95)


def p99_latency_ms(latencies: list[float]) -> float | None:
    """Return 99th percentile of latencies in ms, or None if empty."""
    return _percentile(latencies, 0.99)


def _duration_minutes_from_db(conn) -> float | None:
    """Compute run duration in minutes from min/max created_at in DB."""
    rows = get_all_runs(conn)
    if not rows:
        return None
    timestamps = [r[COL_TS] for r in rows if r[COL_TS]]
    if not timestamps:
        return None
    try:
        parsed = [datetime.fromisoformat(ts.replace("Z", "+00:00")) for ts in timestamps]
        delta = max(parsed) - min(parsed)
        return max(0.001, delta.total_seconds() / 60.0)
    except (ValueError, TypeError):
        return None


def _run_time_window_from_db(conn) -> tuple[str | None, str | None]:
    """Return (min_created_at, max_created_at) as ISO strings, or (None, None) if no data."""
    rows = get_all_runs(conn)
    if not rows:
        return (None, None)
    timestamps = [r[COL_TS] for r in rows if r[COL_TS]]
    if not timestamps:
        return (None, None)
    return (min(timestamps), max(timestamps))


def _check_failure_rates(
    url_fail: int,
    url_total: int,
    upl_fail: int,
    upl_total: int,
) -> list[str]:
    """Compare failure rates and return anomaly messages."""
    anomalies: list[str] = []
    
    url_rate = url_fail / url_total if url_total else 0
    upl_rate = upl_fail / upl_total if upl_total else 0
    
    if url_fail > upl_fail and url_total > 0:
        anomalies.append(
            f"**Failure rate:** `/url` had more failures ({url_fail} vs {upl_fail}); "
            f"failure rate {100 * url_rate:.1f}% vs {100 * upl_rate:.1f}% for `/upload`."
        )
    elif upl_fail > url_fail and upl_total > 0:
        anomalies.append(
            f"**Failure rate:** `/upload` had more failures ({upl_fail} vs {url_fail}); "
            f"failure rate {100 * upl_rate:.1f}% vs {100 * url_rate:.1f}% for `/url`."
        )
    return anomalies


def _check_latency_spreads(
    url_metrics: dict,
    upload_metrics: dict,
) -> list[str]:
    """Compare latency spreads (p95, p99) and return anomaly messages."""
    anomalies: list[str] = []
    url_total = url_metrics.get("total", 0)
    upl_total = upload_metrics.get("total", 0)

    for metric in ("p95", "p99"):
        u_val = url_metrics.get(metric)
        up_val = upload_metrics.get(metric)
        if u_val is not None and up_val is not None and url_total and upl_total:
            diff = abs(u_val - up_val)
            threshold = 0.15 * max(u_val, up_val)
            if diff >= threshold:
                winner = "url" if u_val < up_val else "upload"
                anomalies.append(
                    f"**$L_{{{metric}}}$ spread:** `/{winner}` has lower {metric.upper()} latency "
                    f"({min(u_val, up_val):.0f} ms vs {max(u_val, up_val):.0f} ms)."
                )
    return anomalies


def _detect_anomalies(
    url_metrics: dict,
    upload_metrics: dict,
) -> list[str]:
    """Identify anomalies by comparing metrics."""
    url_fail = url_metrics.get("failures", 0)
    url_total = url_metrics.get("total", 0)
    upl_fail = upload_metrics.get("failures", 0)
    upl_total = upload_metrics.get("total", 0)
    
    if url_total == 0 and upl_total == 0:
        return ["No run data available for comparison."]

    anomalies = _check_failure_rates(url_fail, url_total, upl_fail, upl_total)
    anomalies.extend(_check_latency_spreads(url_metrics, upload_metrics))
    return anomalies


def _recommend_endpoints(
    url_metrics: dict,
    upload_metrics: dict,
) -> list[str]:
    """Generate recommendations based on stability and latency."""
    rec_stability: list[str] = []
    rec_latency: list[str] = []
    
    url_total = url_metrics.get("total", 0)
    upl_total = upload_metrics.get("total", 0)
    
    if url_total == 0 or upl_total == 0:
        return [
            "Run both endpoints to get a recommendation.",
            "Run both endpoints to compare latency and throughput."
        ]

    url_fail = url_metrics.get("failures", 0)
    upl_fail = upload_metrics.get("failures", 0)
    url_rate = url_fail / url_total
    upl_rate = upl_fail / upl_total

    if url_rate < upl_rate:
        rec_stability.append("**Prefer `/url`** for stability (lower failure rate).")
    elif upl_rate < url_rate:
        rec_stability.append("**Prefer `/upload`** for stability (lower failure rate).")
    else:
        rec_stability.append("Both endpoints showed similar failure rates.")

    url_p95 = url_metrics.get("p95")
    upl_p95 = upload_metrics.get("p95")
    
    if url_p95 is not None and upl_p95 is not None:
        if url_p95 < upl_p95:
            rec_latency.append(f"**Prefer `/url`** for latency ($L_{{p95}}$: {url_p95:.0f} ms vs {upl_p95:.0f} ms).")
        elif upl_p95 < url_p95:
            rec_latency.append(f"**Prefer `/upload`** for latency ($L_{{p95}}$: {upl_p95:.0f} ms vs {url_p95:.0f} ms).")
        else:
            rec_latency.append("P95 latency is comparable between endpoints.")

    url_fpm = url_metrics.get("throughput")
    upl_fpm = upload_metrics.get("throughput")
    
    if url_fpm is not None and upl_fpm is not None:
        better = "url" if url_fpm >= upl_fpm else "upload"
        rec_latency.append(f"Throughput $T_{{files/min}}$ is higher for **`/{better}`**.")

    return rec_stability + rec_latency


def _generate_ai_summary(
    url_metrics: dict,
    upload_metrics: dict,
) -> list[str]:
    """
    Rule-based anomaly detection and recommendation comparing /url vs /upload.
    Returns Markdown lines for the AI Agent Summary section.
    """
    lines: list[str] = []
    
    anomalies = _detect_anomalies(url_metrics, upload_metrics)
    lines.append("### Anomaly detection")
    for a in anomalies:
        lines.append(f"- {a}")
    lines.append("")

    recommendations = _recommend_endpoints(url_metrics, upload_metrics)
    lines.append("### Recommendation")
    for r in recommendations:
        lines.append(f"- {r}")
    lines.append("")
    
    lines.append("---")
    lines.append("*Summary generated from benchmark data (rule-based analysis).*")
    return lines


def _write_run_details(lines: list[str], report_ts: str, start_ts: str | None, end_ts: str | None, mode: str, concurrency: int):
    lines.append("# intelliExtract Benchmark — Executive Summary\n")
    lines.append("## Run details")
    lines.append(f"- **Report generated at:** {report_ts}")
    if start_ts and end_ts:
        lines.append(f"- **Run time window:** {start_ts} → {end_ts}")
    lines.append(f"- **Run mode:** {mode}")
    lines.append(f"- **Concurrency:** {concurrency}\n")


def _get_metrics_for_endpoint(conn, endpoint: str, duration_min: float | None) -> dict:
    rows = get_runs_by_endpoint(conn, endpoint)
    total = len(rows)
    successes = [r for r in rows if r[COL_STATUS] == STATUS_SUCCESS]
    latencies = [r[COL_LATENCY_MS] for r in successes if r[COL_LATENCY_MS] is not None]
    fail_count = total - len(successes)
    p95 = p95_latency_ms(latencies)
    p99 = p99_latency_ms(latencies)
    throughput = (len(successes) / duration_min) if duration_min and duration_min > 0 else None
    
    return {
        "total": total,
        "successes": len(successes),
        "failures": fail_count,
        "latencies": latencies, # Needed for mean calculation in report
        "p95": p95,
        "p99": p99,
        "throughput": throughput,
    }


def _write_endpoint_section(lines: list[str], endpoint: str, m: dict, duration_min: float | None):
    lines.append(f"## Endpoint: `{endpoint}`")
    lines.append(f"- Total requests: {m['total']}")
    lines.append(f"- Successes: {m['successes']}")
    lines.append(f"- Failures: {m['failures']}")
    lines.append("")
    lines.append("### Latency (formal notation)")
    lines.append(f"- $L_{{p95}}$ (95th percentile): **{m['p95']:.2f} ms**" if m['p95'] is not None else r"- $L_{p95}$: N/A")
    lines.append(f"- $L_{{p99}}$ (99th percentile): **{m['p99']:.2f} ms**" if m['p99'] is not None else r"- $L_{p99}$: N/A")
    if m['latencies']:
        lines.append(f"- Mean: {statistics.mean(m['latencies']):.2f} ms")
    lines.append("")
    if duration_min and duration_min > 0:
        lines.append("### Throughput")
        lines.append(f"- $T_{{files/min}}$ (files per minute): **{m['throughput']:.2f}**")
    lines.append("")


def _write_failure_breakdown(lines: list[str], conn):
    fail_counts = get_failure_counts_by_type(conn)
    if fail_counts:
        lines.append("## Failure Breakdown")
        lines.append("| Error Type | Count |")
        lines.append("|------------|-------|")
        for row in fail_counts:
            etype = row["error_type"] or "Unknown"
            count = row["count"]
            lines.append(f"| {etype} | {count} |")
        lines.append("")


def _write_slowest_files(lines: list[str], conn):
    slowest = get_slowest_runs(conn, limit=5)
    if slowest:
        lines.append("## Top 5 Slowest Files")
        lines.append("| File | Endpoint | Latency (ms) |")
        lines.append("|------|----------|--------------|")
        for row in slowest:
            lines.append(f"| {row[COL_FILE]} | {row[COL_ENDPOINT]} | {row[COL_LATENCY_MS]:.2f} |")
        lines.append("")


def generate_report(
    db_path: str | Path,
    output_path: str | Path,
    run_mode: str = "dual",
    concurrency: int = 10,
    run_duration_sec: float | None = None,
) -> None:
    """Read SQLite, compute metrics, and write Executive Summary."""
    conn = get_connection(db_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    duration_min = None
    if run_duration_sec is not None and run_duration_sec > 0:
        duration_min = run_duration_sec / 60.0
    if duration_min is None:
        duration_min = _duration_minutes_from_db(conn)

    report_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    start_ts, end_ts = _run_time_window_from_db(conn)

    lines: list[str] = []
    _write_run_details(lines, report_ts, start_ts, end_ts, run_mode, concurrency)

    endpoint_metrics: dict = {}
    for endpoint in ("url", "upload"):
        m = _get_metrics_for_endpoint(conn, endpoint, duration_min)
        endpoint_metrics[endpoint] = m
        _write_endpoint_section(lines, endpoint, m, duration_min)

    _write_failure_breakdown(lines, conn)
    _write_slowest_files(lines, conn)

    lines.append("## AI Agent Summary")
    lines.extend(
        _generate_ai_summary(
            endpoint_metrics.get("url", {}),
            endpoint_metrics.get("upload", {}),
        )
    )

    conn.close()
    output_path.write_text("\n".join(lines), encoding="utf-8")
