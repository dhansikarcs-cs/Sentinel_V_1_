# Sentinel — Incubation Document Pack

Prepared for incubation-centre evaluation · 2026
Main repository: https://github.com/anomalyco/opencode (local: `sentinel3`)

## Document map

| # | Document | What it answers |
|---|----------|-----------------|
| 01 | Executive Summary | What is this, and why does it matter (2 pages) |
| 02 | Research Paper | The full technical/clinical research write-up (21 pages) |
| 03 | White Paper | Industry positioning: problem, solution, security, TCO |
| 04 | Validation & Timing Report | Everything tested + measured timing accuracy |
| 05 | Technical Design Document | Architecture, modules, data model |
| 06 | Business Plan | Market, business model, competition, milestones |
| 07 | Market & Opportunity Database | Opportunity scoring across segments |
| 08 | Hardware Roadmap | Ring SDK (M0 done) through M1–M3, sensory room |
| 09 | Demo & Evaluation Guide | How to run the app and script a 10-minute demo |
| 10 | Deployment & Setup Guide | End-to-end install/run instructions |
| 11 | Team & Credentials | **Template — fill in before submitting** |
| 12 | Engineering Decisions | Key architectural trade-offs and rationale |
| 13 | Judges' Prep Q&A | Anticipated evaluator questions with answers |
| LICENSE | — | Apache 2.0 |

## Suggested reading order for evaluators

1. **01 Executive Summary** — 2 minutes
2. **09 Demo & Evaluation Guide** — run it yourself
3. **04 Validation & Timing Report** — the numbers
4. **03 White Paper / 06 Business Plan** — positioning & commercial case
5. **02 Research Paper / 05 Technical Design** — deep dive

## Reproduce every number

```
cd backend
python -m benchmarks.runner --csv benchmarks/logbook_benchmark.csv   # 47 timed runs
python -m pytest tests -q                                            # 98 tests
```

## Regenerate the PDFs

```
python generate_paper.py              # 02 Research Paper
python generate_whitepaper.py         # 03 White Paper
python generate_validation_report.py  # 04 Validation & Timing Report
python generate_kiot_docs.py          # 01, 06, 09
```

*Copyright 2026 Sentinel Ecosystem (Independent Research). Licensed under the Apache License, Version 2.0.*
