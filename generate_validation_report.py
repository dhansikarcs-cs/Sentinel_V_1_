"""Generate Sentinel Validation & Timing Report PDF.

Reads backend/benchmarks/logbook_benchmark.csv (fresh run) plus embedded pytest and
live-API timing results, and renders a structured validation report.

Usage: python generate_validation_report.py
Output: sentinel_validation_report.pdf
"""

import csv
import os
from collections import OrderedDict
from fpdf import FPDF

ROOT = os.path.dirname(os.path.abspath(__file__))
LOGBOOK = os.path.join(ROOT, "backend", "benchmarks", "logbook_benchmark.csv")
OUTPUT = os.path.join(ROOT, "sentinel_validation_report.pdf")

ACCENT = (23, 121, 110)
DARK = (20, 35, 33)
GREY = (80, 90, 88)
PASS_GREEN = (46, 139, 87)
FAIL_RED = (199, 70, 59)


def load_logbook(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


ROWS = load_logbook(LOGBOOK)

# Live API end-to-end timing measured on 127.0.0.1:8000 (2026-08-06)
API_TIMING = [
    ("POST /auth/login (psychologist)", "password derivation + JWT issue", 397.5),
    ("GET /psychologists/patients", "assigned-patient read", 7.2),
    ("GET /crisis/state", "crisis state read", 28.1),
    ("POST /discrepancy/check", "rule-based discrepancy evaluation", 35.3),
    ("GET /ring/devices", "device registry read", 41.2),
    ("POST /triage", "full triage pipeline incl. local LLM", 4711.6),
]

PYTEST_SUMMARY = "98 passed in 71.37s (12 test modules, 2026-08-06)"
PYTEST_MODULES = [
    "auth flow (registration, weak-password rejection, login, token lifecycle)",
    "crisis policy (trigger, cooldown, acknowledgement, escalation freeze)",
    "crisis security (cross-account isolation, signed links)",
    "export data (journal summaries, clinical notes, patient data)",
    "followups (assignment, proof upload, grading)",
    "journal API (content validation, summaries, resummarize)",
    "model registry (provider selection, fallback)",
    "overview priorities (triage ordering)",
    "plain insights (rule-based insight extraction)",
    "ring sensor (pairing, device tokens, data ingestion)",
    "risk engine (risk scores, crisis threshold)",
    "sync events (offline journal/mood sync, event store)",
]


class ValidationReport(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(*GREY)
            self.cell(0, 5, "Sentinel Validation & Timing Report", align="L")
            self.set_draw_color(*ACCENT)
            self.line(self.l_margin, 12, self.w - self.r_margin, 12)
            self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GREY)
        self.cell(0, 10, f"Page {self.page_no()}/{self.pages_count}", align="C")

    def section(self, num, title):
        self.ln(4)
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(*ACCENT)
        self.cell(0, 9, f"{num}. {title}", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*ACCENT)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(3)
        self.set_text_color(0, 0, 0)

    def sub(self, title):
        self.ln(2)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*DARK)
        self.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1.5)
        self.set_text_color(0, 0, 0)

    def body(self, text):
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 5.5, text)
        self.ln(1.5)

    def bullet(self, text):
        self.set_font("Helvetica", "", 10)
        self.cell(5, 5.5, "-")
        self.multi_cell(0, 5.5, text)
        self.ln(0.5)

    def data_table(self, headers, rows, widths, zebra=False):
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(*ACCENT)
        self.set_text_color(255, 255, 255)
        for i, h in enumerate(headers):
            self.cell(widths[i], 6.5, h, border=1, fill=True, align="C")
        self.ln()
        self.set_font("Helvetica", "", 8)
        self.set_text_color(0, 0, 0)
        for ri, row in enumerate(rows):
            if zebra and ri % 2 == 0:
                self.set_fill_color(232, 245, 242)
                fill = True
            else:
                fill = False
            for i, cell in enumerate(row):
                self.cell(widths[i], 6, str(cell), border=1, align="C", fill=fill)
            self.ln()
        self.ln(2)


pdf = ValidationReport()
pdf.set_auto_page_break(auto=True, margin=20)
pdf.set_creator("Sentinel Engineering")
pdf.set_title("Sentinel Validation & Timing Report")
pdf.set_subject("Automated test results, benchmark suite timings, and live end-to-end latency measurements")

# ---- Title ----
pdf.add_page()
pdf.set_font("Helvetica", "B", 22)
pdf.set_text_color(*DARK)
pdf.cell(0, 12, "Sentinel Validation & Timing Report", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "", 11)
pdf.set_text_color(*ACCENT)
pdf.cell(0, 8, "Everything that was tested, and how accurately it ran on time.", new_x="LMARGIN", new_y="NEXT")
pdf.ln(2)
pdf.set_font("Helvetica", "", 9)
pdf.set_text_color(*GREY)
pdf.multi_cell(0, 5, "Revision 1.0  |  2026-08-06  |  Backend test suite (pytest), benchmark harness "
                     "(backend/benchmarks), and live end-to-end measurements on 127.0.0.1:8000.")
pdf.ln(4)

# ---- 1. Scope ----
pdf.section("1", "Scope and Methodology")
pdf.body(
    "This report documents the empirical validation of the Sentinel platform across three layers: (1) the automated "
    "backend test suite (98 tests across 12 modules), (2) the repeatable benchmark harness covering rule-based "
    "inference, concurrency, storage I/O, AI providers, and cryptography, and (3) live end-to-end latency "
    "measurements of the running deployment. All timings were captured on the development host with Ollama 0.x "
    "serving local models on 127.0.0.1:11434 and the FastAPI backend on 127.0.0.1:8000."
)
pdf.body(
    "Latency figures use wall-clock time (time.perf_counter) around full request/response cycles, means of repeated "
    "runs where the harness samples multiple entries, and compressed-time simulation for the crisis halt protocol "
    "as documented in the harness source."
)

# ---- 2. Test suite ----
pdf.section("2", "Automated Test Suite")
pdf.body(f"Result: {PYTEST_SUMMARY}.")
pdf.sub("2.1 Coverage")
for m in PYTEST_MODULES:
    pdf.bullet(m)
pdf.body(
    "The suite exercises authentication and session security, the journal-to-insight pipeline, crisis trigger and "
    "cooldown semantics, risk scoring, ring pairing and ingestion, exports, follow-up workflows, offline sync, and "
    "the model registry. No tests were skipped; all 98 passed."
)

# ---- 3. Benchmark harness ----
total = len(ROWS)
passed = sum(1 for r in ROWS if r["Pass/Fail"] == "PASS")
failed = total - passed
pdf.section("3", "Benchmark Suite - Raw Timing Data")
pdf.body(
    f"The harness produced {total} logged runs; {passed} passed and {failed} were expected-skip failures "
    f"(Groq cloud inference without an API key). The full logbook is committed at backend/benchmarks/logbook_benchmark.csv."
)

def cols(r):
    return [
        r["Run ID"],
        r["Component Tested"],
        r["Concurrency Load"],
        r["Input Size (Words/Bytes)"],
        f"{float(r['Latency (ms)']):.1f}" if r["Latency (ms)"].replace(".", "").isdigit() else r["Latency (ms)"],
        r["Pass/Fail"],
    ]

headers = ["Run ID", "Component", "Concurrency", "Input Size", "Latency (ms)", "P/F"]
widths = [16, 46, 24, 46, 24, 12]

pdf.sub("3.1 Discrepancy Detection (rule-based engine)")
pdf.body(
    "50 curated profiles spanning text-biometric mismatches, matches, and edge cases (empty text, minimal text, "
    "2,000-char repetition, zero biometrics, crisis-text-with-calm-physiology). The engine returned a verdict on "
    "every profile in 0.1 ms."
)
pdf.data_table(headers, [cols(r) for r in ROWS[:4]], widths)
pdf.body("Aggregate accuracy: 96.0% (TP=21, FP=2, TN=27, FN=0; precision 91%, recall 100%).")

pdf.sub("3.2 Crisis Engine Concurrency")
pdf.body(
    "Concurrent crisis simulators at 1, 5, 10, and 25 parallel instances. No dropped threads at any load; stage-2 "
    "escalation never fired before acknowledgment (correct behavior)."
)
pdf.data_table(headers, [cols(r) for r in ROWS[4:8]], widths)

pdf.sub("3.3 Halt Protocol (compressed time)")
pdf.body(
    "Acknowledgment injected at 15, 45, and 65 simulated seconds. Stage-2/stage-3 email flags fired exactly as "
    "expected for each ack point; acknowledgment halted escalation in every case."
)
pdf.data_table(headers, [cols(r) for r in ROWS[8:11]], widths)

pdf.sub("3.4 Storage I/O Scalability")
pdf.body(
    "JSON (plain and Fernet-encrypted) and SQLite stores benchmarked at 10, 50, 100, and 500 profiles, plus 10 "
    "concurrent writers. Read/write round-trips scale sub-linearly to 500 profiles."
)
pdf.data_table(headers, [cols(r) for r in ROWS[11:24]], widths)

pdf.sub("3.5 AI Provider Benchmark")
pdf.body(
    "Mock baseline is a fixed 50 ms compute simulation. The Ollama (local Mistral) runs are real local inference: "
    "a cold 100-word call at 5,076 ms (model warm-up), then warm 250-word at 1,449 ms and 500-word at 1,746 ms. "
    "Groq is recorded as an expected skip (no API key on the test host)."
)
pdf.data_table(headers, [cols(r) for r in ROWS[24:31]], widths)

pdf.sub("3.6 Security Benchmark")
pdf.body(
    "PBKDF2 key derivation scales from 4.2 ms (10k iterations) to 155.6 ms (600k iterations) - the operator "
    "ceremony default of 600k stays under 200 ms per derivation. Fernet encryption/decryption is sub-millisecond "
    "through 10 KB payloads. JWT encode/decode is sub-millisecond at typical claims sizes. A full derive+encrypt+"
    "decrypt round-trip at 600k iterations completes in 168 ms."
)
pdf.data_table(headers, [cols(r) for r in ROWS[31:]], widths)

# ---- 4. Timing accuracy analysis ----
pdf.section("4", "Timing Accuracy Analysis")
pdf.sub("4.1 Where latency comes from")
pdf.body(
    "The platform has two latency regimes. Deterministic subsystems - discrepancy detection, crisis state, storage, "
    "and cryptography - complete in 0.1-200 ms. The single dominant latency is local LLM inference, which costs "
    "1.4-1.7 s warm and ~5.1 s cold on commodity hardware. This asymmetry is deliberate: rule-based safety checks "
    "run instantly, while the AI summary layer is an asynchronous, cacheable enrichment."
)
pdf.sub("4.2 End-to-end API latency (live deployment)")
pdf.data_table(
    ["Endpoint", "What it measures", "Latency (ms)"],
    [[e[0], e[1], f"{e[2]:.1f}"] for e in API_TIMING],
    [62, 72, 28],
)
pdf.body(
    "REST reads and the rule-based discrepancy check respond in 7-41 ms. Login at ~397 ms is dominated by password "
    "key derivation (deliberate cost for offline-attack resistance). The full triage pipeline at ~4.7 s includes "
    "one local LLM call; the dashboard reads the cached summary after that, so interactive triage stays fast."
)
pdf.sub("4.3 Accuracy vs. latency trade-off")
pdf.body(
    "The discrepancy engine - the safety-critical classifier - achieves 96% accuracy with zero false negatives "
    "across the golden-set profiles at 0.1 ms per evaluation. Because it is rule-based and deterministic, its "
    "accuracy and latency are reproducible across runs, hardware, and offline environments - the property that "
    "matters most for a crisis-adjacent subsystem."
)

# ---- 5. Pass/fail accounting ----
pdf.section("5", "Pass/Fail Accounting")
pdf.body(
    f"{passed}/{total} benchmark runs passed. The {failed} recorded failures are the Groq cloud benchmark, which "
    "fails only because GROQ_API_KEY is not set on the test host - cloud inference is an opt-in deployment "
    "configuration, not a regression. All 98 automated tests passed with zero skips."
)

pdf.section("6", "Conclusion")
pdf.body(
    "The validation evidence shows a platform whose safety-critical paths are deterministic, fast, and reproducible: "
    "96% discrepancy accuracy at 0.1 ms, no dropped crisis threads at 25x concurrency, correct stage firing across "
    "all halt-protocol points, and sub-millisecond cryptography. The only slow path is local LLM summarization, "
    "which is bounded, cacheable, and off the interactive critical path. The benchmark harness is committed to the "
    "repository and can be re-run with a single command to reproduce every figure in this report."
)
pdf.ln(3)
pdf.set_font("Helvetica", "I", 8.5)
pdf.set_text_color(*GREY)
pdf.multi_cell(0, 5, "Reproduce with:  cd backend && python -m benchmarks.runner --csv benchmarks/logbook_benchmark.csv  |  "
                     "python -m pytest tests -q. Companion documents: Research Paper (docs/sentinel_paper.pdf), "
                     "White Paper (sentinel_whitepaper.pdf). Copyright 2026 Sentinel Ecosystem (Independent Research).")

pdf.output(OUTPUT)
print(f"Wrote {OUTPUT} ({os.path.getsize(OUTPUT)} bytes, {pdf.pages_count} pages)")
