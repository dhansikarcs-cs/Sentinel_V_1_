"""Generate the missing incubation-centre documents into kiot/.

Outputs:
  kiot/01_Executive_Summary.pdf
  kiot/06_Business_Plan.pdf
  kiot/09_Demo_and_Evaluation_Guide.pdf

Usage: python generate_kiot_docs.py
"""

import os
from fpdf import FPDF

ROOT = os.path.dirname(os.path.abspath(__file__))
KIOT = os.path.join(ROOT, "kiot")

ACCENT = (23, 121, 110)
DARK = (20, 35, 33)
GREY = (80, 90, 88)


class KiotDoc(FPDF):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(22, 22, 22)
        self.set_creator("Sentinel Engineering")

    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(*GREY)
            self.cell(0, 5, self._t, align="L")
            self.set_draw_color(*ACCENT)
            self.line(self.l_margin, 12, self.w - self.r_margin, 12)
            self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GREY)
        self.cell(0, 10, f"Page {self.page_no()}/{self.pages_count}", align="C")

    def title_block(self, title, subtitle, doc):
        self._t = title
        self.set_title(title)
        self.set_subject(subtitle)
        self.add_page()
        self.set_font("Helvetica", "B", 20)
        self.set_text_color(*DARK)
        self.cell(0, 12, title, new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 11)
        self.set_text_color(*ACCENT)
        self.cell(0, 8, subtitle, new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(*GREY)
        self.cell(0, 6, doc, new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def section(self, num, title):
        self.ln(3)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*ACCENT)
        self.cell(0, 8, f"{num}. {title}", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*ACCENT)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2.5)
        self.set_text_color(0, 0, 0)

    def sub(self, title):
        self.ln(1.5)
        self.set_font("Helvetica", "B", 10.5)
        self.set_text_color(*DARK)
        self.cell(0, 6.5, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)
        self.set_text_color(0, 0, 0)

    def body(self, text):
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 5.5, text)
        self.ln(1.2)

    def mission(self, text):
        self.ln(1)
        self.set_fill_color(232, 245, 242)
        self.set_draw_color(*ACCENT)
        self.set_font("Helvetica", "I", 11)
        self.set_text_color(20, 90, 82)
        self.multi_cell(0, 6, text, border=1, fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(3)

    def bullet(self, text):
        self.set_font("Helvetica", "", 10)
        self.cell(5, 5.5, "-")
        self.multi_cell(0, 5.5, text)
        self.ln(0.4)

    def table(self, headers, rows, widths):
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(*ACCENT)
        self.set_text_color(255, 255, 255)
        for i, h in enumerate(headers):
            self.cell(widths[i], 6.5, h, border=1, fill=True, align="C")
        self.ln()
        self.set_font("Helvetica", "", 8)
        self.set_text_color(0, 0, 0)
        for row in rows:
            for i, c in enumerate(row):
                self.cell(widths[i], 6, str(c), border=1, align="C")
            self.ln()
        self.ln(1.5)


# ──────────────────────────────────────────────────────────────
# 1. Executive Summary
# ──────────────────────────────────────────────────────────────
p = KiotDoc()
p.title_block(
    "Sentinel - Executive Summary",
    "On-Premises Psychophysiological Triage Node",
    "Prepared for incubation evaluation  |  2026  |  Companion: White Paper, Validation & Timing Report, Business Plan",
)

p.section("1", "The Product")
p.body(
    "Sentinel is a hardware-software infrastructure for continuous mental health support that connects three "
    "stakeholders in one real-time ecosystem: the patient, the psychologist, and the trusted contact. A patient "
    "portal captures biometric signals from wearable smart rings and AI-summarized journal entries. A clinician "
    "dashboard presents triage-ranked patients, AI-synthesized clinical notes, and a live crisis broadcast. A "
    "no-login trusted-contact page provides signed escalation links during crisis events. Every clinical loop - "
    "journal to insight, crisis to acknowledgement, task to graded proof - closes inside the platform."
)
p.mission("Sentinel is designed to support mental health professionals, not replace clinical judgment.")

p.section("2", "The Problem")
p.body(
    "Therapy is confined to weekly sessions while mental health risk evolves continuously between them. Clinicians "
    "carry caseloads with heavy documentation burden, and physiological, textual, and clinical signals live in "
    "separate silos. Crisis support depends on appointment availability - and often on a single point of failure."
)

p.section("3", "The Solution")
p.bullet("Fused signal pipeline: physiology (HR, HRV, stress, sleep, SpO2) + 28-label GoEmotions emotion "
         "classification + self-reported mood, correlated to surface cross-signal discrepancies.")
p.bullet("Deterministic crisis engine: staged escalation (patient siren, trusted-contact email, helpline), haltable "
         "by clinician acknowledgement at any point, with cooldown throttling.")
p.bullet("Privacy-first AI: primary inference runs fully offline via a local 7.2B-parameter therapy-tuned model "
         "(Ollama); cloud AI is opt-in.")
p.bullet("Zero-infrastructure cost: open-source stack (FastAPI + React PWA), SQLite/PostgreSQL, no per-seat or "
         "per-inference fees.")
p.bullet("Hardware-agnostic: pluggable RingSource SDK (BLE, vendor cloud, simulator); hardware M0 complete, OEM "
         "ring in procurement.")

p.section("4", "Validation Highlights")
p.table(
    ["Claim", "Measured result"],
    [
        ["Automated test suite", "98/98 tests passed, 12 modules, 0 skips"],
        ["Discrepancy accuracy", "96.0% (Prec 91%, Rec 100%), 0.1 ms per evaluation"],
        ["Crisis engine concurrency", "102-109 ms at 1-25 concurrent, 0 dropped threads"],
        ["Halt protocol", "Stages fire correctly at 15/45/65 s ack points"],
        ["Local AI summarization", "1.4-1.7 s warm, ~5.1 s cold (Mistral, commodity hardware)"],
        ["REST API latency", "7-41 ms on live deployment"],
        ["Full AI triage pipeline", "~4.7 s end-to-end incl. one local LLM call"],
        ["Security primitives", "PBKDF2 4-156 ms; Fernet <2 ms; JWT ~0.5 ms"],
    ],
    [62, 100],
)
p.body(
    "Full raw run IDs and methodology are in the Validation & Timing Report; every figure is reproducible with two "
    "commands from the repository."
)

p.section("5", "Why Sentinel Stands Out")
p.bullet("Ecosystem, not app: three synchronized interfaces over one state layer.")
p.bullet("AI that assists but never decides - explainable, deterministic safety paths.")
p.bullet("On-premises + offline inference = data never leaves the clinic.")
p.bullet("Works on consumer smart rings and runs at zero monthly operating cost.")

p.section("6", "Stage and Ask")
p.body(
    "Sentinel is an independent research project with a working, fully tested implementation. The current ask of an "
    "incubation program is: infrastructure support for live hardware pilots, clinical-partner access for validation "
    "studies, and mentorship on regulatory pathways (clinical software, privacy compliance). Milestones and the "
    "commercial plan are detailed in the Business Plan (06)."
)

p.output(os.path.join(KIOT, "01_Executive_Summary.pdf"))
print("01_Executive_Summary.pdf", p.pages_count, "pages")

# ──────────────────────────────────────────────────────────────
# 2. Business Plan
# ──────────────────────────────────────────────────────────────
p = KiotDoc()
p.title_block(
    "Sentinel - Business Plan",
    "Market opportunity, business model, competition, and milestones",
    "Prepared for incubation evaluation  |  2026  |  Companion: Executive Summary, White Paper",
)

p.section("1", "Market Opportunity")
p.body(
    "The mental-health technology market is growing at double-digit rates globally, driven by clinician shortage, "
    "rising demand for continuous care, and post-pandemic acceptance of digital mental health. Sentinel targets the "
    "underserved middle: institutions that need real-time, clinically integrated monitoring but cannot accept "
    "per-seat SaaS costs, cloud-data residency risks, or black-box AI decisions."
)
p.table(
    ["Segment", "Who they are", "What Sentinel offers"],
    [
        ["Counselling centres & clinics", "Private practices, hospital psychiatry depts", "Between-session monitoring, crisis safety net, triage dashboards"],
        ["Universities & campuses", "Student mental health offices", "Low-cost deployment, offline privacy, trusted-contact loop"],
        ["Low-resource / rural settings", "Clinics with limited IT staff", "Zero-infrastructure cost, commodity hardware, PWA access"],
        ["Research institutions", "Psychophysiology / HCI labs", "Open, auditable pipeline; ring SDK; event store for studies"],
    ],
    [44, 56, 62],
)

p.section("2", "Business Model")
p.bullet("Primary: on-premises software license + support for clinics and institutions (per-site annual license, "
         "unlimited users/seats).")
p.bullet("Hardware bundle: optional smart-ring kit (BLE gateway + rings) for programs that want turnkey physical "
         "deployment; margin on hardware.")
p.bullet("Research tier: free academic license in exchange for published validation data (cohort studies).")
p.bullet("Cost structure is exceptional: software stack, storage, and local AI are zero-cost; the platform has no "
         "recurring cloud bill, enabling thin margins at low prices.")
p.body(
    "Revenue levers are the software license, the hardware bundle, and later a managed hosted tier for customers "
    "who prefer SaaS over on-prem. Offline-first architecture means even the hosted tier uses the customer's local "
    "inference, keeping marginal compute cost near zero."
)

p.section("3", "Competition")
p.table(
    ["Competitor", "Model", "Gap Sentinel fills"],
    [
        ["Wellness apps (generic)", "B2C subscriptions", "No clinician integration, no real-time escalation"],
        ["Telehealth platforms", "Per-session B2B", "Appointment-only; nothing between sessions"],
        ["Mental-health chatbots", "B2C AI chat", "No physiology, no clinical workspace, black-box AI"],
        ["Wearable vendor dashboards", "B2C analytics", "Patient-only data; no psychologist or contact loop"],
        ["Crisis helplines", "Public service", "Standalone; no continuity of care"],
    ],
    [54, 46, 62],
)
p.body(
    "No competitor combines continuous physiology, emotion-labelled language, a deterministic crisis escalation "
    "loop, an offline AI path, and a tri-directional stakeholder loop in a single auditable system."
)

p.section("4", "Go-to-Market and Milestones")
p.bullet("Phase 1 (now): pilot with 1-2 counselling centres / a university counselling office; hardware M0 complete.")
p.bullet("Phase 2 (next): clinical validation study with a partner institution; live BLE/vendor ring ingestion (M1).")
p.bullet("Phase 3: campus-scale deployment, published validation, research-tier academic adoption.")
p.bullet("Phase 4: managed hosted tier + FHIR-adjacent export for regulated clinical use.")

p.section("5", "Financial Summary")
p.table(
    ["Item", "Assumption", "Value"],
    [
        ["Operating cost", "Open-source stack + local AI + SQLite/PostgreSQL", "$0/month recurring"],
        ["Revenue stream", "Per-site annual license (pilots at intro pricing)", "TBD at pilot"],
        ["Hardware bundle", "OEM ring + BLE gateway per program", "Margin on cost"],
        ["Funding ask", "Pilot infrastructure + partner access + regulatory mentorship", "Incubation program"],
    ],
    [44, 66, 52],
)

p.section("6", "Risks and Mitigations")
p.bullet("Clinical acceptance: mitigated by explainable, deterministic safety paths and AI-as-assistant posture.")
p.bullet("Regulatory path: mitigated by on-prem data residency, audit log, signed links, and encryption defaults.")
p.bullet("Hardware dependency: mitigated by vendor-agnostic RingSource SDK and a full deterministic simulator for "
         "software-only pilots.")
p.body(
    "Full technical detail, security posture, and measured performance are documented in the White Paper and "
    "Validation & Timing Report."
)
p.output(os.path.join(KIOT, "06_Business_Plan.pdf"))
print("06_Business_Plan.pdf", p.pages_count, "pages")

# ──────────────────────────────────────────────────────────────
# 3. Demo & Evaluation Guide
# ──────────────────────────────────────────────────────────────
p = KiotDoc()
p.title_block(
    "Sentinel - Demo and Evaluation Guide",
    "How to run the platform and what to show in a 10-minute walkthrough",
    "Prepared for incubation evaluation  |  2026  |  Live deployment: http://localhost:8000",
)

p.section("1", "Prerequisites")
p.bullet("Python 3.11+ with backend requirements installed (backend/requirements.txt).")
p.bullet("Node 18+; frontend at frontend/ builds with tsc + Vite into frontend/dist (served by the backend).")
p.bullet("Ollama running locally with the `sentinel` (or `mistral`) model pulled - provides offline AI inference.")

p.section("2", "Run the Stack")
p.bullet("Backend:  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000  (from backend/).")
p.bullet("Frontend: already built to frontend/dist and served at http://localhost:8000 by the backend.")
p.bullet("Rebuild frontend after changes:  node node_modules/typescript/bin/tsc -b  then  node "
         "node_modules/vite/bin/vite.js build  (from frontend/).")
p.bullet("Seed demo data:  python seed_demo.py  (from backend/).")

p.section("3", "Demo Accounts")
p.table(
    ["Role", "Username", "Password"],
    [
        ["Psychologist", "cel", "1234"],
        ["Patient", "alaya", "4321"],
    ],
    [50, 56, 56],
)

p.section("4", "10-Minute Walkthrough Script")
p.sub("4.1 Patient portal (2 min)")
p.bullet("Log in as alaya. Show biometric trends (BPM, stress, sleep, SpO2, mood) on the dashboard.")
p.bullet("Open an AI journal summary; note the 28-label emotion classification feeding the summary.")
p.sub("4.2 Psychologist triage (3 min)")
p.bullet("Log in as cel. Open the Priority Triage Dashboard: patients are ranked by risk score; expand a patient "
         "to see the five bio metric cards, the AI clinical insight, and the explainability panel.")
p.bullet("Trigger the 'Why this summary?' panel to show the traceable, non-black-box reasoning.")
p.sub("4.3 Crisis escalation (3 min)")
p.bullet("From the patient view, trigger a crisis (or POST /api/crisis/trigger). Watch it appear live on the "
         "psychologist dashboard, then acknowledge it to freeze the escalation timer.")
p.bullet("Explain the staged protocol: patient siren, trusted-contact signed email, helpline escalation, halt-on-ack.")
p.sub("4.4 Validation artifacts (2 min)")
p.bullet("Show backend/benchmarks/logbook_benchmark.csv (47 timed runs) and quote the headline numbers: 96% "
         "discrepancy accuracy at 0.1 ms, 98/98 tests, 1.4-1.7 s local AI, 7-41 ms REST.")
p.bullet("Reproduce live:  cd backend && python -m benchmarks.runner && python -m pytest tests -q.")

p.section("5", "What Evaluators Can Check Themselves")
p.bullet("Security: bcrypt policy, JWT rotation, Fernet field encryption, hash-chained audit log, signed links.")
p.bullet("Privacy: the local-AI path sends no data off-device; cloud AI is off by default.")
p.bullet("Openness: full source in the repository; benchmark and test harness committed; docs regenerate from "
         "scripts in the root.")
p.body(
    "Companion documents: White Paper (03), Validation & Timing Report (04), Technical Design (05), Deployment & "
    "Setup Guide (10)."
)
p.output(os.path.join(KIOT, "09_Demo_and_Evaluation_Guide.pdf"))
print("09_Demo_and_Evaluation_Guide.pdf", p.pages_count, "pages")

# ──────────────────────────────────────────────────────────────
# 4. Pitch & Demo Guide
# ──────────────────────────────────────────────────────────────
p = KiotDoc()
p.title_block(
    "Sentinel - Pitch and Demo Guide",
    "Current stage, roadmap, support needed, and your three spoken demos",
    "Prepared for Dhansika  |  Incubation visit  |  Live app demo",
)

p.section("1", "Start With the Story")
p.body(
    "Mental health professionals often work under time pressure while trying to understand complex patient data. "
    "Sentinel was created to support - not replace - their clinical decision-making, by bringing the right "
    "information together in one place: a patient's physiology, their own words, and the context a clinician "
    "needs to act."
)
p.mission("Sentinel is designed to support mental health professionals, not replace clinical judgment.")
p.body(
    "Then describe the system in one breath: a patient wears a smart ring and journals; the platform fuses "
    "physiology, language, and mood; a deterministic crisis engine escalates through a staged protocol that any "
    "psychologist can halt with one tap; and the whole thing runs offline at zero monthly cost."
)

p.section("2", "Current Stage - Where Sentinel Is Today")
p.bullet("Done: Research completed.")
p.bullet("Done: AI architecture designed.")
p.bullet("Done: Working software prototype - 98/98 tests passing, benchmarked end to end.")
p.bullet("Done: Documentation completed (research paper, white paper, validation report).")
p.bullet("Next: Clinical validation (planned).")
p.bullet("Next: Hardware prototype / live ring pilot (planned).")
p.bullet("Next: Pilot deployment (planned).")

p.section("3", "Roadmap - One Page")
p.bullet("Research (complete) - literature, architecture, psychophysiological foundation.")
p.bullet("Prototype (complete) - working dual-portal software with crisis engine and offline AI.")
p.bullet("Clinical validation (next) - a partner institution, a defined cohort, measured outcomes.")
p.bullet("Pilot - one counselling centre or university counselling office running daily.")
p.bullet("Hardware - live BLE/vendor ring ingestion at scale (M0 SDK is already done).")
p.bullet("Deployment - campus or clinic-wide rollout on commodity hardware.")
p.bullet("Scaling - multi-site deployment, managed tier, FHIR-adjacent export for regulated use.")
p.body(
    "Read it as a staircase: each stage unlocks the next, and the two steps below the current line are already "
    "finished and verifiable."
)

p.section("4", "Support Needed - How the Incubator Can Help")
p.bullet("Clinical mentorship - guidance from practising psychologists and psychiatrists.")
p.bullet("Validation guidance - designing a sound clinical validation study.")
p.bullet("Product feedback - iterating the interface with real users.")
p.bullet("Industry connections - clinics, universities, and wearable device makers.")
p.bullet("Regulatory guidance - the path to compliance and clearance.")
p.bullet("Grants for hardware pilot testing - funding for more rings and devices so a real pilot can run.")
p.body(
    "Be specific when asked: the fastest help is a clinical partner for a validation pilot and access to hardware "
    "for real-world ring testing."
)

p.section("5", "Your Three Demos")
p.sub("5.1  Thirty seconds (elevator)")
p.body(
    "Sentinel is a mental-health platform that connects patients, psychologists, and trusted contacts in real time. "
    "A patient wears a smart ring and journals; the system fuses physiology, language, and mood to flag risk early. "
    "When a patient is in crisis, it escalates automatically through a staged protocol that any psychologist can "
    "stop with one tap. It runs fully offline on open-source software at zero monthly cost - and it is designed to "
    "support clinicians, not replace them. It is already built and tested."
)
p.sub("5.2  Two minutes (room pitch)")
p.body(
    "Mental health professionals are under time pressure and patient risk evolves between sessions. Most tools "
    "only see one signal - an app, a wearable, a chat. [Open the app.] This is Sentinel. The patient portal captures "
    "biometric trends from a smart ring and AI-summarized journals, with emotion labels - 28 categories - feeding "
    "every summary. The psychologist side ranks patients by risk and auto-expands crisis cases. The key piece is "
    "the crisis engine: a staged escalation - patient feedback, trusted-contact email with a signed link, then "
    "helpline - that a clinician halts with one tap. Everything is explainable, and the AI path runs locally, so no "
    "patient data leaves the clinic. It is validated: 98 tests passing, 96 percent discrepancy accuracy at 0.1 "
    "milliseconds. Today it is at the clinical-validation stage, and that is exactly where I need an incubator's help."
)
p.sub("5.3  Five minutes (full walkthrough)")
p.bullet("0:00-0:30 Story opener: the sentence from section 1.")
p.bullet("0:30-1:30 Log in as the patient (alaya): show biometric trends and one AI journal summary with emotion "
         "labels; note the warm patient-facing tone.")
p.bullet("1:30-3:00 Log in as the psychologist (cel): open the triage dashboard, expand a patient to show the five "
         "bio metric cards and the clinical insight, then open the 'Why this summary?' explainability panel.")
p.bullet("3:00-4:00 Trigger a crisis from the patient view; show it appear live on the psychologist dashboard; "
         "acknowledge it and point out the frozen escalation timer. Name the staged protocol.")
p.bullet("4:00-5:00 Close with validation: 98/98 tests, 96% discrepancy accuracy, 0.1 ms rule engine, 1.4-1.7 s "
         "local AI, 7-41 ms REST. End on the one-line ask: clinical partner + hardware for a validation pilot.")
p.body(
    "Full click-through instructions and demo accounts are in 09_Demo_and_Evaluation_Guide. Rehearse each script "
    "out loud at least three times - especially the 30-second one."
)

p.section("6", "Notes Before Tomorrow")
p.bullet("You are the product as much as the documents are - lead with the story, then the numbers.")
p.bullet("Keep the app warm: start the backend and Ollama, and click through the demo twice before presenting.")
p.bullet("If the live demo fails, fall back to the 2-minute room pitch - it needs no screen.")
p.bullet("You built this alone, as a 10th-grade student, over three years of independent research - say it plainly "
         "once; it is a strength, not a caveat.")
p.body(
    "Companion documents: Executive Summary (01), Validation & Timing Report (04), Demo & Evaluation Guide (09), "
    "Team & Credentials (11)."
)
p.output(os.path.join(KIOT, "14_Pitch_and_Demo_Guide.pdf"))
print("14_Pitch_and_Demo_Guide.pdf", p.pages_count, "pages")
