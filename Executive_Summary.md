# intelliExtract Benchmark — Executive Summary

## Run details
- **Report generated at:** 2026-02-10T19:58:25Z
- **Run time window:** 2026-02-10 19:37:33 → 2026-02-10 19:58:25
- **Run mode:** dual
- **Concurrency:** 10

## Endpoint: `url`
- Total requests: 100
- Successes: 100
- Failures: 0

### Latency (formal notation)
- $L_{p95}$ (95th percentile): **4502.19 ms**
- $L_{p99}$ (99th percentile): **4738.28 ms**
- Mean: 2626.02 ms

### Throughput
- $T_{files/min}$ (files per minute): **191.18**

## Endpoint: `upload`
- Total requests: 100
- Successes: 100
- Failures: 0

### Latency (formal notation)
- $L_{p95}$ (95th percentile): **5400.53 ms**
- $L_{p99}$ (99th percentile): **6279.57 ms**
- Mean: 2841.79 ms

### Throughput
- $T_{files/min}$ (files per minute): **191.18**

## Top 5 Slowest Files
| File | Endpoint | Latency (ms) |
|------|----------|--------------|
| 192922353-1782615-MAR-Backup.xlsx | upload | 6453.40 |
| 194173402-DEE-10102864-Supplier-Billback.xlsx | upload | 6279.57 |
| 193636777-DEE-10026115-Supplier-Billback.xlsx | upload | 5998.06 |
| 191694390-DEE-9844907-Supplier-Billback.xlsx | url | 5920.73 |
| 184340490-DEE-9514754-Supplier-Billback.csv | upload | 5581.61 |

## AI Agent Summary
### Anomaly detection
- **$L_{p95}$ spread:** `/url` has lower P95 latency (4502 ms vs 5401 ms).
- **$L_{p99}$ spread:** `/url` has lower P99 latency (4738 ms vs 6280 ms).

### Recommendation
- Both endpoints showed similar failure rates.
- **Prefer `/url`** for latency ($L_{p95}$: 4502 ms vs 5401 ms).
- Throughput $T_{files/min}$ is higher for **`/url`**.

---
*Summary generated from benchmark data (rule-based analysis).*