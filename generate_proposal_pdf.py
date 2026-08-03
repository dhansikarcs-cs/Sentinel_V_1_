"""Generate proposal PDF from 500-word markdown. Engineering + human voice."""

from fpdf import FPDF
import os

OUTPUT = os.path.join(os.path.dirname(__file__), "sentinel_proposal.pdf")


class ProposalPDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 8)
            self.cell(0, 5, "Sentinel Ecosystem Proposal", align="C")
            self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def section_title(self, num, title):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(30, 30, 80)
        self.cell(0, 10, f"{num}. {title}", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(30, 30, 80)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)
        self.set_text_color(0, 0, 0)

    def subsection(self, title):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(50, 50, 50)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self.set_text_color(0, 0, 0)

    def body(self, text):
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def bullet(self, text):
        self.set_font("Helvetica", "", 10)
        x = self.get_x()
        self.cell(5, 5.5, "•")
        self.multi_cell(0, 5.5, text)
        self.ln(1)

    def blockquote(self, text):
        self.set_font("Helvetica", "I", 10)
        self.set_text_color(80, 80, 80)
        self.set_x(self.l_margin + 5)
        self.multi_cell(0, 5.5, text)
        self.set_text_color(0, 0, 0)
        self.ln(3)


pdf = ProposalPDF()
pdf.alias_nb_pages()
pdf.set_auto_page_break(auto=True, margin=20)
pdf.add_page()

# Title block
pdf.set_font("Helvetica", "B", 22)
pdf.set_text_color(30, 30, 80)
pdf.cell(0, 12, "The Sentinel Ecosystem", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "", 13)
pdf.set_text_color(60, 60, 60)
pdf.cell(0, 8, "Hardware-Software Infrastructure for Clinical Resilience", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(3)
pdf.set_font("Helvetica", "I", 10)
pdf.set_text_color(80, 80, 80)
pdf.cell(0, 6, "Systems Engineering Proposal - Bridging the Psychiatric Monitoring Gap", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(6)

# ==== 1. THE PROBLEM ====
pdf.section_title("1", "THE PROBLEM - A SYSTEM UNDER STRAIN")

pdf.body(
    "Mental healthcare runs on a reactive model. A patient shows up for their weekly session, "
    "talks for 50 minutes, and then goes back into the world for another 167 hours with nobody "
    "watching. That is where things fall apart. Crises develop between the cracks. Tasks go "
    "undone. Patients sit alone with their thoughts and no feedback loop."
)
pdf.body(
    "On the other side of the desk, the numbers are worse. India runs 0.75 psychiatrists per "
    "100,000 people. The WHO says you need at least 1 per 10,000. That is a 13x gap. Clinicians "
    "carry caseloads nobody designed them to handle, drowning in paperwork, progress notes, and "
    "the emotional weight of everyone elses trauma. Secondary stress is baked into the job."
)
pdf.body(
    "You end up with a dual failure: patients lack any continuous support layer, and clinicians "
    "burn out from administrative overload. Nobody wins."
)
pdf.body(
    "Existing solutions do not fix this. Telehealth platforms give you appointment-only access. "
    "Crisis helplines average 3-5 minute wait times - forever when you are in distress. Wellness "
    "apps are generic and disconnected from the clinical loop. None of them connect patient, "
    "psychologist, and trusted contact in a single real-time system. None of them combine what "
    "your body is saying with what you wrote in your journal."
)

# ==== 2. THE ECOSYSTEM ====
pdf.section_title("2", "THE SENTINEL ECOSYSTEM  -  NOT A PROJECT, AN INFRASTRUCTURE")

pdf.body(
    "Sentinel is a hardware-software infrastructure, not another app. Three things make it "
    "different from anything out there."
)
pdf.body(
    "Tri-directional stakeholder loop. Most platforms serve one person. Sentinel serves three - "
    "patient, psychologist, and trusted contact - through synchronized interfaces. A patient "
    "writes a journal entry. The psychologist sees the summary on their triage board. If the "
    "crisis engine fires, the trusted contact gets an alert too. Everyone sees the same reality "
    "at the same time."
)
pdf.body(
    "Hardware-software integration. Biometric data from a wearable ring feeds into the same "
    "assessment pipeline as journal text. Heart rate variability, sleep patterns, stress levels - "
    "analyzed alongside subjective mood and written reflection. One unified stream instead of "
    "siloed dashboards."
)
pdf.body(
    "End-to-end workflow closure. Crisis trigger to acknowledgment. Task assignment to graded "
    "feedback. Booking submission to status notification. Every loop closes inside the ecosystem. "
    "Nothing falls out."
)

pdf.subsection("2.1 Patient Portal")
pdf.body(
    "Patients get a daily journal with AI summarization that works in two modes: a warm "
    "personal reflection for them, and a structured clinical OAP note for their psychologist. "
    "Mood tracking locks one entry per day - no retrospective filling. Emotion classification "
    "covers 28 GoEmotions labels (sadness, fear, nervousness, etc.) feeding into every summary. "
    "Biometric trends from the ring show alongside the text. Session booking works from a "
    "dropdown of available dates. One-tap crisis trigger activates automatically when biometrics "
    "and emotional trends cross the threshold."
)

pdf.subsection("2.2 Psychologist Portal")
pdf.body(
    "Clinicians see only their assigned patients, sorted by crisis priority. AI-synthesized "
    "clinical notes in OAP format save hours of documentation time. Follow-up tasks get assigned "
    "and graded with proof-based completion - patients upload evidence, psychologists score it. "
    "Booking management with accept/waitlist. Encrypted session notes. "
    "The AI sidebar gives pre-session briefs, cross-patient pattern detection, and alerts when "
    "a patient has been silent too long."
)

pdf.subsection("2.3 Adaptive Smart Room  -  Shared Sensory Modulation")
pdf.body(
    "The smart room adjusts lighting (amber shift for calming, cool for alertness), sound "
    "(low-frequency pink noise at 60-200 Hz), and scent (lavender, vanilla) based on real-time "
    "physiological state. Crucially, it reads both the patient and the psychologist simultaneously. "
    "When both are elevated, the environment modulates for the dyad - creating a shared calming "
    "field rather than leaving the clinician to regulate alone."
)
pdf.body(
    "The current configuration is a prototype foundation. The architecture supports scaling from "
    "a single biometric ring with a web dashboard to a full sensory clinic room. Future iterations "
    "use a plugin system for additional sensors and actuators."
)

pdf.subsection("2.4 Crisis Engine")
pdf.body(
    "When a patient hits the emergency trigger, three things happen on a timer: "
    "0-29 seconds: local audiovisual siren on the patient dashboard. "
    "At 30 seconds: the trusted contact gets an email with an acknowledgment link - no login "
    "required, just click to confirm. "
    "At 60 seconds: helpline escalation if nobody has acknowledged yet. "
    "If the psychologist acknowledges at any stage, everything stops and we record resolution time. "
    "The halt is instantaneous."
)

# ==== 3. AI ====
pdf.section_title("3", "AI AS ASSISTANT, NOT REPLACEMENT")

pdf.body(
    "The AI never makes clinical decisions. Full stop. It does not diagnose, does not prescribe, "
    "does not override anything a human decides. Its role is strictly supportive."
)
pdf.body(
    "The custom sentinel model (fine-tuned 7.2B parameters via Ollama) produces empathy-toned "
    "reflections for patients and structured clinical notes for psychologists. A TF-IDF emotion "
    "classifier over 28 GoEmotions labels tags journal text. Echo detection prevents the AI from "
    "just parroting the patients own words back at them - a surprisingly common failure mode in "
    "off-the-shelf models."
)
pdf.body(
    "If a clinic needs absolute data privacy, the model runs entirely offline via Ollama - no data "
    "leaves the building. Cloud deployments can use Groq API for speed. Three-tier fallback ensures "
    "you never get a blank response: Ollama local first, Groq remote second, rule-based extraction "
    "last. The crisis engine and discrepancy classifier never touch any external API."
)

# ==== 4. SCIENCE ====
pdf.section_title("4", "SCIENTIFIC FOUNDATION  -  BIOLOGY MEETS PSYCHOLOGY")

pdf.body(
    "Sentinel's assessment approach works because the body tells the story before the mind does. "
    "Research shows elevated resting heart rate and disrupted sleep precede self-reported emotional "
    "deterioration by hours or days. By combining biometric and emotional streams into a single "
    "pipeline, you catch the signal earlier."
)
pdf.body(
    "Three data layers feed the engine: "
    "Biometric data from the ring - heart rate, stress levels, sleep duration, SpO2, mood - "
    "deterministically seeded per user per hour. "
    "Emotional data from journal text, analyzed across 28 emotion labels via a TF-IDF + "
    "LogisticRegression classifier. "
    "A discrepancy detector that flags mismatches between what the body says and what the text "
    "says - because a patient writing I am fine with a heart rate of 120 is not fine."
)
pdf.body(
    "The emotion classifier runs locally as a 4 MB Python pickle. No cloud dependency. "
    "Deterministic inference. Zero neural black boxes."
)

# ==== 5. SELF-CARE ====
pdf.section_title("5", "SELF-CARE FOR THE CLINICIAN")

pdf.body(
    "The psychologist dashboard includes self-monitoring metrics - cumulative session load, "
    "average escalation response time, and passive biometric trends from their own ring if they "
    "wear one. This is not surveillance. It is awareness. Secondary traumatic stress and fatigue "
    "creep up slowly. A dashboard that shows you the data helps you catch it before it catches you."
)

# ==== 6. DEPLOYMENT ====
pdf.section_title("6", "ACCESSIBILITY & DEPLOYMENT")

pdf.body(
    "The entire platform runs on free-tier infrastructure. Ollama handles local inference - no GPU "
    "required, runs on any machine with 8 GB RAM. Groq handles cloud fallback. The backend is "
    "FastAPI on uvicorn, frontend is React with Vite, both containerized and deployable with a "
    "single docker-compose up. SQLite in WAL mode replaces the earlier JSON storage, giving us "
    "transaction-safe operations across 15 database tables."
)
pdf.body(
    "Zero financial barrier for any clinic, school, or community center. No licensing fees. No per-seat "
    "pricing. No vendor lock-in. Everything runs on your own hardware or a free Render instance."
)

# Save
pdf.output(OUTPUT)
print(f"PDF written to {OUTPUT}")
print(f"Size: {os.path.getsize(OUTPUT)} bytes")
print(f"Pages: {pdf.page_no()}")
