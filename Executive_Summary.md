# intelliExtract Benchmark — Executive Summary

## Run details
- **Report generated at:** 2026-03-05T12:03:55Z
- **Run time window:** 2026-03-05 12:03:46 → 2026-03-05 12:03:55
- **Run mode:** dual
- **Concurrency:** 10

## Benchmark Summary
| Metric | Value |
|--------|-------|
| **Duration** | 10.64s |
| **Total Tasks** | 10 |
| **`/url` Success** | 5 / 5 (100.0%) |
| **`/upload` Success** | 5 / 5 (100.0%) |

## Endpoint: `url`
- Total requests: 5
- Successes: 5
- Failures: 0

### Latency Breakdown
| Component | Mean (ms) | P50 (ms) | P90 (ms) | P95 (ms) | P99 (ms) |
|-----------|-----------|----------|----------|----------|----------|
| **Total Latency** (client round-trip) | 6545.71 | 5497.46 | 8223.50 | 8223.50 | 8223.50 |
| Server Processing (App Runner) | 5370.40 | 4332.00 | 7034.00 | 7034.00 | 7034.00 |
| Client Network Overhead (TCP/TLS/transfer) | 1175.31 | 1162.46 | 1189.50 | 1189.50 | 1189.50 |

### Throughput
- $T_{files/min}$ (files per minute): **28.18**

## Endpoint: `upload`
- Total requests: 5
- Successes: 5
- Failures: 0

### Latency Breakdown
| Component | Mean (ms) | P50 (ms) | P90 (ms) | P95 (ms) | P99 (ms) |
|-----------|-----------|----------|----------|----------|----------|
| **Total Latency** (client round-trip) | 7742.31 | 7700.02 | 10625.64 | 10625.64 | 10625.64 |
| Server Processing (App Runner) | 6562.40 | 6534.00 | 9425.00 | 9425.00 | 9425.00 |
| Client Network Overhead (TCP/TLS/transfer) | 1179.91 | 1166.02 | 1191.64 | 1191.64 | 1191.64 |

### Throughput
- $T_{files/min}$ (files per minute): **28.18**

## Top 5 Slowest Files
| File | Endpoint | Latency (ms) |
|------|----------|--------------|
| 1768815841608-DEE-11313174.xlsx | upload | 10636.39 |
| 184340490-DEE-9514754-Supplier-Billback.csv | upload | 10625.64 |
| 24769724-332531a3-1b5c-4ba9-b5b8-125530702fde.xlsx | upload | 8405.60 |
| 1768815841608-DEE-11313174.xlsx | url | 8249.56 |
| 183901325-DEE-9509477-Supplier-Billback.csv | url | 8223.50 |

## AI Agent Summary
### Anomaly detection
- **$L_{p95}$ spread:** `/url` has lower P95 latency (8224 ms vs 10626 ms).
- **$L_{p99}$ spread:** `/url` has lower P99 latency (8224 ms vs 10626 ms).

### Recommendation
- Both endpoints showed similar failure rates.
- **Prefer `/url`** for latency ($L_{p95}$: 8224 ms vs 10626 ms).
- Throughput $T_{files/min}$ is higher for **`/url`**.

---
*Summary generated from benchmark data (rule-based analysis).*