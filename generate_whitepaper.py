"""Generate Sentinel white paper PDF.

Usage: python generate_whitepaper.py
Output: sentinel_whitepaper.pdf (industry/technical positioning document)
"""

from fpdf import FPDF
import os

OUTPUT = os.path.join(os.path.dirname(__file__), "sentinel_whitepaper.pdf")

ACCENT = (23, 121, 110)      # Sentinel teal
DARK = (20, 35, 33)
GREY = (80, 90, 88)


class WhitePaper(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(*GREY)
            self.cell(0, 5, "Sentinel White Paper  |  On-Premises Psychophysiological Triage Node", align="L")
            self.set_draw_color(*ACCENT)
            self.line(self.l_margin, 12, self.w - self.r_margin, 12)
            self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GREY)
        self.cell(0, 10, f"Page {self.page_no()}/{self.pages_count}", align="C")

    def cover(self):
        self.add_page()
        self.set_margins(24, 24, 24)
        y = self.get_y()
        self.set_fill_color(*DARK)
        self.rect(0, 0, self.w, y + 150, "F")
        self.set_y(y + 34)
        self.set_font("Helvetica", "B", 26)
        self.set_text_color(255, 255, 255)
        self.cell(0, 12, "SENTINEL", align="C")
        self.ln(14)
        self.set_font("Helvetica", "", 15)
        self.cell(0, 8, "On-Premises Psychophysiological Triage Node", align="C")
        self.ln(10)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(190, 220, 214)
        self.multi_cell(0, 6, "A hardware-software infrastructure that connects patients, psychologists, and "
                              "trusted contacts through continuous biometric monitoring, AI-assisted journal analysis, "
                              "and a deterministic crisis escalation protocol.", align="C")
        self.ln(14)
        self.set_draw_color(*ACCENT)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(255, 255, 255)
        self.cell(0, 6, "Independent Research Project  |  2026", align="C")
        self.ln(16)
        self.set_font("Helvetica", "I", 9)
        self.cell(0, 6, "Technology White Paper", align="C")
        self.set_y(120)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(200, 210, 208)
        self.multi_cell(0, 5, "Companion documents: Sentinel Research Paper (docs/sentinel_paper.pdf), "
                              "Sentinel Validation & Timing Report (sentinel_validation_report.pdf).", align="C")

    def section_title(self, num, title):
        self.ln(4)
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(*ACCENT)
        self.cell(0, 9, f"{num}. {title}", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*ACCENT)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(3)
        self.set_text_color(0, 0, 0)

    def subsection(self, title):
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
        x = self.get_x()
        self.cell(5, 5.5, "-")
        self.multi_cell(0, 5.5, text)
        self.ln(0.5)

    def table(self, headers, rows, widths=None):
        if widths is None:
            widths = [self.w / len(headers)] * len(headers)
        self.set_font("Helvetica", "B", 8.5)
        self.set_fill_color(*ACCENT)
        self.set_text_color(255, 255, 255)
        for i, h in enumerate(headers):
            self.cell(widths[i], 7, h, border=1, fill=True, align="C")
        self.ln()
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(0, 0, 0)
        for row in rows:
            for i, cell in enumerate(row):
                self.cell(widths[i], 6.5, str(cell), border=1, align="C")
            self.ln()
        self.ln(2)


pdf = WhitePaper()
pdf.set_auto_page_break(auto=True, margin=20)
pdf.set_creator("Sentinel Engineering")
pdf.set_title("Sentinel White Paper - On-Premises Psychophysiological Triage Node")
pdf.set_subject("Continuous mental health infrastructure: biometric monitoring, AI journal analysis, crisis escalation")

pdf.cover()

pdf.add_page()
pdf.section_title("1", "Executive Summary")
pdf.body(
    "Sentinel is an on-premises, hardware-software infrastructure for continuous mental health support. It unifies "
    "three stakeholders - the patient, the psychologist, and the trusted contact - into a single real-time ecosystem. "
    "A patient-facing portal captures biometric signals from wearable smart rings and AI-summarized journal entries. "
    "A clinician dashboard presents triage-ranked patients with AI-synthesized clinical notes and an active-crisis "
    "broadcast. A no-login trusted-contact page provides signed escalation links during crisis events."
)
pdf.body(
    "The system was designed around one conviction: crisis support cannot depend on appointment availability. By "
    "fusing physiology, language, and self-report into one assessment pipeline, Sentinel surfaces cross-signal "
    "discrepancies (a patient writing \"I'm okay\" while biometric trends show escalating stress) and escalates "
    "deterministically through a staged crisis protocol. The platform is open-source, deploys to commodity hardware, "
    "runs its primary AI inference fully offline, and has a validated measurement burden of under 5 milliseconds for "
    "rule-based engines and 1.4-5.1 seconds for local LLM summarization."
)

pdf.section_title("2", "The Problem")
pdf.subsection("2.1 The Between-Sessions Gap")
pdf.body(
    "The therapeutic relationship is confined to weekly or biweekly sessions. Between appointments, patients "
    "experience emotional fluctuation and, in critical cases, crisis states without a channel for intervention. "
    "Telehealth platforms offer appointment-only connectivity; wellness apps provide generic content without "
    "clinician integration; crisis helplines operate as standalone services with no continuity of care."
)
pdf.subsection("2.2 Clinician Overload")
pdf.body(
    "WHO data indicates a global median of 0.75 psychiatrists per 100,000 people in low-resource settings. "
    "Clinicians carry caseloads that require continuous monitoring, documentation, triage, and follow-up - "
    "administrative burden that displaces therapeutic presence and drives burnout."
)
pdf.subsection("2.3 Fragmented Signals")
pdf.body(
    "Biometric wearables, journal text, and clinical notes live in separate silos. Cross-signal patterns - a "
    "physiological marker that precedes self-reported deterioration by 24-48 hours - remain undetected until they "
    "manifest as crisis."
)

pdf.section_title("3", "The Sentinel Solution")
pdf.body(
    "Sentinel is a modular, dual-portal platform over a shared state layer (SQLite/PostgreSQL). Three integrated "
    "subsystems close every clinical loop inside the ecosystem."
)
pdf.subsection("3.1 Patient Portal")
pdf.bullet("Biometric trend visualization: heart rate, stress, sleep, SpO2, and mood.")
pdf.bullet("AI-summarized journaling with daily mood tracking and 28-label GoEmotions emotion classification.")
pdf.bullet("Session booking, follow-up tasks with proof-based completion, and a one-tap crisis trigger.")
pdf.subsection("3.2 Psychologist Portal")
pdf.bullet("Triage-ranked patient list; crisis cases auto-expand with live state.")
pdf.bullet("Dual-mode AI documentation: warm patient reflection and structured OAP clinical notes.")
pdf.bullet("Follow-up grading (green/yellow/red), booking accept/waitlist queue, and an AI clinician sidebar "
           "(pre-session briefs, relapse indicators, silent-period watch, cross-patient patterns).")
pdf.subsection("3.3 Trusted Contact Portal")
pdf.bullet("Standalone no-login page reachable only via HMAC-signed, expiring links.")
pdf.bullet("One-tap acknowledgment and \"I'm on my way\" response reflected live to the clinician.")
pdf.subsection("3.4 Hardware Abstraction Layer")
pdf.body(
    "Sentinel does not build proprietary wearables. A pluggable RingSource SDK supports BLE GATT (bleak), vendor "
    "cloud APIs, and a deterministic simulator through one abstract base class. Devices authenticate via SHA-256 "
    "hashed device tokens compared in constant time. Hardware M0 (ring SDK + device binding) is complete; an OEM "
    "ring is in procurement."
)

pdf.section_title("4", "Crisis Engine - Deterministic Escalation")
pdf.body(
    "The crisis engine implements a time-sensitive, multi-stage escalation protocol with no single point of "
    "failure: Stage 1 siren feedback on the patient device (0-29s); Stage 2 email to the trusted contact with a "
    "signed acknowledgment link (30s); Stage 3 helpline escalation (60s). Psychologist acknowledgment at any point "
    "halts all escalation, freezes the response timer, and records resolution duration."
)
pdf.body(
    "Activation is driven by an explainable risk engine (score 1-10) blending keyword signals, emotion-classifier "
    "probabilities, and a temporal trend. Automatic activation fires at the crisis threshold and is throttled by a "
    "3600-second cooldown so repeated entries cannot fire the full protocol repeatedly."
)

pdf.section_title("5", "AI as Assistant, Not Replacement")
pdf.body(
    "Sentinel's design principle is that AI supports but never decides. The system does not diagnose, prescribe, "
    "or override clinical judgment. Functions are strictly supportive:"
)
pdf.bullet("Journal summarization in a warm patient mode (custom 7.2B-parameter therapy-tuned `sentinel` Ollama model).")
pdf.bullet("Clinical note synthesis into Observations-Assessment-Plan format.")
pdf.bullet("Local TF-IDF + LogisticRegression emotion classifier (GoEmotions, 28 labels, ~4 MB pickle) that feeds "
           "emotion hints into summarization.")
pdf.bullet("Echo detection that prevents the AI from parroting raw patient text (word-overlap >85% triggers a fallback).")
pdf.bullet("Three-tier fallback: local `sentinel` model, then Groq Cloud, then rule-based extraction - AI never fails silently.")
pdf.subsection("5.1 Privacy-First Inference")
pdf.body(
    "The primary AI path runs entirely on local hardware via Ollama - no patient data leaves the local network, "
    "and no internet connection is required. Cloud AI is disabled by default and enabled only by explicit operator "
    "opt-in with encrypted transport."
)

pdf.section_title("6", "Security and Data Protection")
pdf.body(
    "Sentinel treats clinical data protection as an architectural requirement, not an add-on:"
)
pdf.bullet("bcrypt password hashing with strict policy; per-account lockout after repeated failures.")
pdf.bullet("HS256 JWT access tokens with refresh-token rotation; HttpOnly cookie session storage.")
pdf.bullet("Field-level transparent encryption (Fernet) under a PBKDF2-600K-derived key activated by an operator "
           "passphrase ceremony; clinical notes encrypted per psychologist.")
pdf.bullet("Hash-chained append-only audit log and a transactional event store for replay.")
pdf.bullet("CORS lockdown, per-IP rate limiting, input sanitization (SQL-injection and XSS rejection), and global "
           "error handlers that never leak stack traces.")
pdf.bullet("Signed, expiring trusted-contact links (HMAC) that cannot be guessed, replayed, or repurposed.")
pdf.body(
    "Security subsystems are continuously benchmarked - PBKDF2 derivation cost, Fernet round-trip overhead, JWT "
    "handshake, and encrypted storage scaling are part of the nightly validation suite (see the Validation & "
    "Timing Report)."
)

pdf.section_title("7", "Measured Performance")
pdf.body(
    "Sentinel ships with a repeatable benchmark harness (backend/benchmarks) that records latency, concurrency, "
    "and resource usage in an IRIS-style logbook. Results from the latest automated run:"
)
pdf.table(
    ["Subsystem", "Measurement", "Result"],
    [
        ["Discrepancy engine (rule-based)", "50 profiles", "0.1 ms, 96% accuracy"],
        ["Crisis engine concurrency", "1-25 concurrent", "102-109 ms, 0 dropped"],
        ["Storage I/O (JSON/SQLite)", "10-500 profiles", "23-181 ms round-trip"],
        ["AI summarizer (mock baseline)", "100-500 words", "50-52 ms"],
        ["AI summarizer (Ollama local)", "100-500 words", "1.4-5.1 s TTFT"],
        ["PBKDF2 key derivation", "10k-600k iterations", "4-156 ms"],
        ["Fernet crypto round-trip", "100B-100KB", "0.3-1.8 ms"],
        ["JWT auth handshake", "64B-1KB claims", "0.5 ms typical"],
    ],
    widths=[62, 42, 62],
)
pdf.body(
    "Live end-to-end measurements on the running deployment show REST endpoints at 7-41 ms, login (password "
    "derivation) at ~397 ms, and the full AI triage pipeline at ~4.7 s. Full methodology, raw run IDs, and pass/fail "
    "accounting are documented in the companion Validation & Timing Report."
)

pdf.section_title("8", "Deployment and Total Cost of Ownership")
pdf.body(
    "The platform is designed for zero-cost infrastructure:"
)
pdf.bullet("Backend: FastAPI + SQLAlchemy over SQLite/PostgreSQL (open source).")
pdf.bullet("Frontend: React 19 + TypeScript + Vite, installable PWA with offline app shell and network-first API caching.")
pdf.bullet("AI: local `sentinel` model via Ollama (fully offline) or opt-in Groq Cloud free tier.")
pdf.bullet("Hosting: bare-metal, Docker Compose, or Render.com (free HTTPS, auto-deploy).")
pdf.bullet("Hardware: consumer smart rings via the RingSource SDK; deterministic simulator for development and CI.")
pdf.body(
    "The on-premises posture means clinics and research institutions can operate the full system without any "
    "subscription, per-seat, or inference-per-call cost - a material difference for low-resource settings."
)

pdf.section_title("9", "Roadmap")
pdf.body(
    "Hardware M0 (ring SDK, device binding, authenticated ingestion) is complete and validated. M1-M3 extend "
    "ingestion to live BLE and vendor cloud streams, add multi-device pairing and battery telemetry, and move the "
    "adaptive sensory room (light slewing, acoustic masking, olfactory modulation) from prototype to clinical pilot. "
    "Software work targets expanded longitudinal analytics, standardized export (FHIR-adjacent), and multi-site "
    "PostgreSQL deployment."
)

pdf.section_title("10", "Conclusion")
pdf.body(
    "Sentinel demonstrates that comprehensive, privacy-preserving mental health infrastructure is achievable on "
    "commodity hardware at zero recurring cost. Its differentiation is architectural: tri-directional stakeholder "
    "connectivity, unified psychophysiological signal fusion, deterministic crisis escalation, and an AI layer that "
    "assists without deciding. The full implementation - source, tests, and benchmarks - is open and auditable."
)
pdf.ln(4)
pdf.set_font("Helvetica", "I", 8.5)
pdf.set_text_color(*GREY)
pdf.multi_cell(
    0, 5,
    "Companion documents: Research Paper (docs/sentinel_paper.pdf), Validation & Timing Report "
    "(sentinel_validation_report.pdf), Technical Design (docs/TECHNICAL_DESIGN.md). "
    "Copyright 2026 Sentinel Ecosystem (Independent Research). Licensed under the Apache License, Version 2.0.",
    align="C",
)

pdf.output(OUTPUT)
print(f"Wrote {OUTPUT} ({os.path.getsize(OUTPUT)} bytes, {pdf.pages_count} pages)")
