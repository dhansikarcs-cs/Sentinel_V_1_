"""Benchmark orchestrator — generates IRIS-ready CSV logbook.

Usage: python -m benchmarks.runner [--quick] [--csv out.csv]
TODO: wire into CI pipeline — fail on regressions beyond 5% threshold
"""

import argparse
import csv
import os
import sys
import tracemalloc
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.test_ai_benchmark import run_ai_benchmarks
from benchmarks.test_crisis_concurrency import run_crisis_concurrency_tests
from benchmarks.test_discrepancy import run_discrepancy_tests
from benchmarks.test_security import run_security_benchmarks
from benchmarks.test_storage_scalability import run_storage_benchmarks

LOGBOOK_HEADERS = [
    "Run ID",
    "Component Tested",
    "Concurrency Load",
    "AI Mode",
    "Input Size (Words/Bytes)",
    "Latency (ms)",
    "CPU/RAM Peak",
    "Pass/Fail",
    "Notes / Error Caught",
]

RESULTS: list[dict] = []


def log(component, concurrency, ai_mode, input_size, latency_ms, cpu_ram, passed, notes=""):
    run_id = f"#{len(RESULTS) + 1:04d}"
    RESULTS.append(
        {
            "Run ID": run_id,
            "Component Tested": component,
            "Concurrency Load": str(concurrency),
            "AI Mode": ai_mode,
            "Input Size (Words/Bytes)": str(input_size),
            "Latency (ms)": f"{latency_ms:.1f}",
            "CPU/RAM Peak": cpu_ram,
            "Pass/Fail": "PASS" if passed else "FAIL",
            "Notes / Error Caught": notes,
        }
    )
    status = "PASS" if passed else "FAIL"
    print(f"  {run_id} {component:35s} | {latency_ms:>8.1f}ms | {status}")


def write_csv(path: str):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LOGBOOK_HEADERS)
        w.writeheader()
        w.writerows(RESULTS)
    print(f"\nLogbook written to {path} ({len(RESULTS)} rows)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="Run minimal subset")
    parser.add_argument("--csv", default=None, help="Output CSV path")
    args = parser.parse_args()

    csv_path = args.csv or os.path.join(os.path.dirname(__file__), "logbook_benchmark.csv")

    print("=" * 72)
    print(f"SENTINEL BENCHMARK SUITE — Started {datetime.now(UTC).isoformat()}")
    print("=" * 72)

    tracemalloc.start()

    # 1. Discrepancy Detection
    print("\n>>> [1/4] Discrepancy Detection (50 profiles)")
    run_discrepancy_tests(log, quick=args.quick)

    # 2. Crisis Concurrency
    print("\n>>> [2/4] Crisis Engine Concurrency")
    run_crisis_concurrency_tests(log, quick=args.quick)

    # 3. Storage Scalability
    print("\n>>> [3/4] Storage I/O Scalability")
    run_storage_benchmarks(log, quick=args.quick)

    # 4. AI Benchmark (Groq vs Ollama stubs)
    print("\n>>> [4/4] AI Provider Benchmark")
    run_ai_benchmarks(log, quick=args.quick)

    # 5. Security Benchmark (PBKDF2, crypto overhead, JWT auth)
    print("\n>>> [5/4] Security Benchmark")
    run_security_benchmarks(log, quick=args.quick)

    write_csv(csv_path)

    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"Peak memory during benchmarks: {peak / 1024:.1f} KB")
    print("Done.")


if __name__ == "__main__":
    main()
