# intelliExtract Benchmark — Executive Summary

## Run details
- **Report generated at:** 2026-02-18T12:33:59Z
- **Run time window:** 2026-02-18 12:33:46 → 2026-02-18 12:33:59
- **Run mode:** dual
- **Concurrency:** 10

## Endpoint: `url`
- Total requests: 10
- Successes: 10
- Failures: 0

### Latency (formal notation)
- $L_{p95}$ (95th percentile): **9160.11 ms**
- $L_{p99}$ (99th percentile): **9160.11 ms**
- Mean: 5602.81 ms

### Throughput
- $T_{files/min}$ (files per minute): **37.27**

## Endpoint: `upload`
- Total requests: 10
- Successes: 10
- Failures: 0

### Latency (formal notation)
- $L_{p95}$ (95th percentile): **9638.79 ms**
- $L_{p99}$ (99th percentile): **9638.79 ms**
- Mean: 7533.93 ms

### Throughput
- $T_{files/min}$ (files per minute): **37.27**

## Top 5 Slowest Files
| File | Endpoint | Latency (ms) |
|------|----------|--------------|
| 184978200-DEE-9546763-Supplier-Billback.csv | upload | 9651.58 |
| 184340490-DEE-9514754-Supplier-Billback.csv | upload | 9638.79 |
| 184340490-DEE-9514754-Supplier-Billback.csv | url | 9426.81 |
| 183716217-1727343-MAR-Backup.xlsx | upload | 9388.84 |
| 24769724-332531a3-1b5c-4ba9-b5b8-125530702fde.xlsx | url | 9160.11 |

## AI Agent Summary
### Anomaly detection

### Recommendation
- Both endpoints showed similar failure rates.
- **Prefer `/url`** for latency ($L_{p95}$: 9160 ms vs 9639 ms).
- Throughput $T_{files/min}$ is higher for **`/url`**.

---
*Summary generated from benchmark data (rule-based analysis).*