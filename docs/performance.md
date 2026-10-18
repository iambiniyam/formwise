# Scanned detection performance

Measured on an Apple Silicon Mac with 8 GB RAM.

Workload: the two-page generated PDF used in the detection test, one OCR pass per page.

| Run | Wall time |
|---|---:|
| RapidOCR engine created per page | 1.29 s |
| One cached engine reused | 1.05 s |

Formwise now creates the OCR engine once per process. The saving grows with page count and repeated detection runs.

This measures engine reuse, not OCR accuracy or throughput on real scans.
