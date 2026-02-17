# intelliExtract Benchmark — Executive Summary

## Run details
- **Report generated at:** 2026-02-10T19:07:10Z
- **Run time window:** 2026-02-10 19:07:10 → 2026-02-10 19:07:10
- **Run mode:** dual
- **Concurrency:** 10

## Endpoint: `url`
- Total requests: 5
- Successes: 2
- Failures: 3

### Latency (formal notation)
- $L_{p95}$ (95th percentile): **100.00 ms**
- $L_{p99}$ (99th percentile): **100.00 ms**
- Mean: 150.00 ms

### Throughput
- $T_{files/min}$ (files per minute): **2000.00**

## Endpoint: `upload`
- Total requests: 4
- Successes: 2
- Failures: 2

### Latency (formal notation)
- $L_{p95}$ (95th percentile): **150.00 ms**
- $L_{p99}$ (99th percentile): **150.00 ms**
- Mean: 2575.00 ms

### Throughput
- $T_{files/min}$ (files per minute): **2000.00**

## Failure Breakdown
| Error Type | Count |
|------------|-------|
| Timeout | 3 |
| ServerError | 1 |
| ClientError | 1 |

## Top 5 Slowest Files
| File | Endpoint | Latency (ms) |
|------|----------|--------------|
| slow1.xlsx | upload | 5000.00 |
| file2.xlsx | url | 200.00 |
| file3.xlsx | upload | 150.00 |
| file1.xlsx | url | 100.00 |

## AI Agent Summary
### Anomaly detection
- **Failure rate:** `/url` had more failures (3 vs 2); failure rate 60.0% vs 50.0% for `/upload`.
- **$L_{p95}$ spread:** `/url` has lower P95 latency (100 ms vs 150 ms).
- **$L_{p99}$ spread:** `/url` has lower P99 latency (100 ms vs 150 ms).

### Recommendation
- **Prefer `/upload`** for stability (lower failure rate).
- **Prefer `/url`** for latency ($L_{p95}$: 100 ms vs 150 ms).
- Throughput $T_{files/min}$ is higher for **`/url`**.

---
*Summary generated from benchmark data (rule-based analysis).*