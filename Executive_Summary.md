# intelliExtract Benchmark — Executive Summary

## Run details
- **Report generated at:** 2026-02-18T12:15:28Z
- **Run time window:** 2026-02-18 12:15:15 → 2026-02-18 12:15:28
- **Run mode:** dual
- **Concurrency:** 10

## Endpoint: `url`
- Total requests: 5
- Successes: 5
- Failures: 0

### Latency (formal notation)
- $L_{p95}$ (95th percentile): **14088.12 ms**
- $L_{p99}$ (99th percentile): **14088.12 ms**
- Mean: 7392.44 ms

### Throughput
- $T_{files/min}$ (files per minute): **21.24**

## Endpoint: `upload`
- Total requests: 5
- Successes: 5
- Failures: 0

### Latency (formal notation)
- $L_{p95}$ (95th percentile): **14104.91 ms**
- $L_{p99}$ (99th percentile): **14104.91 ms**
- Mean: 11525.38 ms

### Throughput
- $T_{files/min}$ (files per minute): **21.24**

## Top 5 Slowest Files
| File | Endpoint | Latency (ms) |
|------|----------|--------------|
| 1768815841608-DEE-11313174.xlsx | upload | 14106.19 |
| 24769724-332531a3-1b5c-4ba9-b5b8-125530702fde.xlsx | upload | 14104.91 |
| 1768815841608-DEE-11313174.xlsx | url | 14103.41 |
| 184340490-DEE-9514754-Supplier-Billback.csv | upload | 14094.72 |
| 183716217-1727343-MAR-Backup.xlsx | url | 14088.12 |

## AI Agent Summary
### Anomaly detection

### Recommendation
- Both endpoints showed similar failure rates.
- **Prefer `/url`** for latency ($L_{p95}$: 14088 ms vs 14105 ms).
- Throughput $T_{files/min}$ is higher for **`/url`**.

---
*Summary generated from benchmark data (rule-based analysis).*