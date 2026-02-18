# intelliExtract Benchmark — Executive Summary

## Run details
- **Report generated at:** 2026-02-18T12:19:33Z
- **Run time window:** 2026-02-18 12:19:22 → 2026-02-18 12:19:33
- **Run mode:** dual
- **Concurrency:** 5

## Endpoint: `url`
- Total requests: 5
- Successes: 5
- Failures: 0

### Latency (formal notation)
- $L_{p95}$ (95th percentile): **7679.09 ms**
- $L_{p99}$ (99th percentile): **7679.09 ms**
- Mean: 6536.71 ms

### Throughput
- $T_{files/min}$ (files per minute): **21.09**

## Endpoint: `upload`
- Total requests: 5
- Successes: 5
- Failures: 0

### Latency (formal notation)
- $L_{p95}$ (95th percentile): **6502.15 ms**
- $L_{p99}$ (99th percentile): **6502.15 ms**
- Mean: 6548.77 ms

### Throughput
- $T_{files/min}$ (files per minute): **21.09**

## Top 5 Slowest Files
| File | Endpoint | Latency (ms) |
|------|----------|--------------|
| 184340490-DEE-9514754-Supplier-Billback.csv | url | 7696.38 |
| 1768815841608-DEE-11313174.xlsx | upload | 7696.08 |
| 183901325-DEE-9509477-Supplier-Billback.csv | url | 7679.09 |
| 24769724-332531a3-1b5c-4ba9-b5b8-125530702fde.xlsx | url | 7678.84 |
| 183901325-DEE-9509477-Supplier-Billback.csv | upload | 6502.15 |

## AI Agent Summary
### Anomaly detection
- **$L_{p95}$ spread:** `/upload` has lower P95 latency (6502 ms vs 7679 ms).
- **$L_{p99}$ spread:** `/upload` has lower P99 latency (6502 ms vs 7679 ms).

### Recommendation
- Both endpoints showed similar failure rates.
- **Prefer `/upload`** for latency ($L_{p95}$: 6502 ms vs 7679 ms).
- Throughput $T_{files/min}$ is higher for **`/url`**.

---
*Summary generated from benchmark data (rule-based analysis).*