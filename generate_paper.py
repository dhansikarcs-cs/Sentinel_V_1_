from fpdf import FPDF

class Paper(FPDF):
    def __init__(self):
        super().__init__("P", "mm", "A4")
        self.set_auto_page_break(auto=True, margin=25.4)
        self.set_margins(25.4, 25.4, 25.4)
        self.add_font("AR", "", "C:\\Windows\\Fonts\\arial.ttf")
        self.add_font("AR", "B", "C:\\Windows\\Fonts\\arialbd.ttf")
        self.add_font("AR", "I", "C:\\Windows\\Fonts\\ariali.ttf")
        self.add_font("AR", "BI", "C:\\Windows\\Fonts\\arialbi.ttf")

    def header(self):
        if self.page_no() > 1:
            self.set_font("AR", "I", 9)
            self.set_text_color(128, 128, 128)
            self.cell(0, 8, "Sentinel: On-Premises Psychophysiological Triage Node", align="C")
            self.ln(10)

    def footer(self):
        if self.page_no() > 1:
            self.set_y(-20)
            self.set_font("AR", "", 9)
            self.set_text_color(128, 128, 128)
            self.cell(0, 10, str(self.page_no()), align="C")

    def title_page(self):
        self.add_page()
        self.ln(50)
        self.set_font("AR", "B", 22)
        self.set_text_color(0, 0, 0)
        self.multi_cell(0, 12, "Sentinel:\nAn On-Premises Psychophysiological\nTriage Node for Continuous Mental\nHealth Monitoring", align="C")
        self.ln(20)
        self.set_font("AR", "", 14)
        self.cell(0, 10, "Biomedical Engineering", align="C")
        self.ln(10)
        self.set_font("AR", "", 12)
        self.cell(0, 10, "Submission Year: 2026", align="C")
        self.ln(40)
        self.set_font("AR", "I", 10)
        self.multi_cell(0, 6, "This paper describes the engineering design, security hardening, and empirical validation\nof a low-cost, on-premises platform for continuous psychophysiological monitoring\nand discrepancy detection in outpatient mental health care.", align="C")

    def section(self, num, title):
        self.ln(4)
        self.set_font("AR", "B", 12)
        self.set_text_color(0, 0, 0)
        t = f"{num}. {title}" if num else title
        self.cell(0, 7, t)
        self.ln(8)

    def subsection(self, title):
        self.ln(2)
        self.set_font("AR", "BI", 11)
        self.set_text_color(0, 0, 0)
        self.cell(0, 6, title)
        self.ln(7)

    def body(self, text):
        self.set_font("AR", "", 11)
        self.set_text_color(0, 0, 0)
        self.multi_cell(0, 5.2, text)
        self.ln(2)

    def make_table(self, headers, data, col_w=None):
        if col_w is None:
            col_w = 160 / len(headers)
        self.set_font("AR", "B", 9)
        self.set_fill_color(230, 230, 230)
        self.set_text_color(0, 0, 0)
        for i, h in enumerate(headers):
            self.cell(col_w, 6, h, border=1, align="C", fill=True)
        self.ln()
        self.set_font("AR", "", 9)
        for row in data:
            for i, cell in enumerate(row):
                self.cell(col_w, 5.5, str(cell), border=1, align="C")
            self.ln()
        self.ln(3)

p = Paper()

# ========================================
# TITLE PAGE
# ========================================
p.title_page()

# ========================================
# 1. INTRODUCTION
# ========================================
p.add_page()
p.section("1", "Introduction")
p.body(
    "Mental health disorders represent one of the most significant global health burdens of the "
    "21st century. The shortage of mental health professionals is particularly acute in low- and "
    "middle-income countries. In India, the psychiatrist-to-population ratio is approximately "
    "0.75 per 100,000 people, compared to the WHO minimum recommendation of 1 per 10,000 [1]. "
    "Approximately 60 percent of districts lack any mental health services whatsoever, creating "
    "a fundamental monitoring gap. A patient receiving outpatient care may see a psychiatrist "
    "for one hour per week, leaving 167 hours of unmonitored time during which acute stress, "
    "panic episodes, or suicidal ideation can occur without intervention. "
    "The National Mental Health Survey of India reported that 80 to 85 percent of individuals "
    "with mental health conditions do not receive any treatment, and the economic burden of "
    "mental health conditions costs the global economy an estimated 1 trillion USD annually "
    "in lost productivity. Technology-assisted monitoring offers a scalable alternative that "
    "extends the reach of the existing clinical workforce without requiring a proportional "
    "increase in the number of clinicians."
)
p.body(
    "Beyond improving patient monitoring, an equally important engineering objective is supporting "
    "the sustainability of outpatient mental health practice. Clinical psychologists and psychiatrists "
    "often manage large caseloads while balancing therapy sessions, documentation, follow-up, and "
    "administrative responsibilities. As patient demand continues to outpace workforce growth, manually "
    "reviewing every patient\u2019s condition between appointments becomes increasingly impractical. Rather "
    "than replacing clinical judgment, Sentinel was designed to automate routine monitoring, prioritize "
    "patients showing meaningful psychophysiological discrepancies, and present clinicians with actionable "
    "information that helps them allocate their limited time more efficiently. By reducing repetitive "
    "monitoring tasks and directing attention toward patients requiring intervention, the system aims "
    "to improve continuity of care while supporting more scalable outpatient mental health services."
)
p.body(
    "Existing digital mental health platforms predominantly rely on cloud-based architectures that "
    "transmit patient data to remote servers for storage and analysis. While these systems offer "
    "convenience for well-connected clinics, they introduce latency, connectivity dependency, and "
    "data sovereignty concerns that are particularly problematic for low-resource or offline clinical "
    "environments [2]. A clinic in a rural area with intermittent internet connectivity cannot rely "
    "on cloud-based assessment for time-sensitive triage decisions. Furthermore, many existing "
    "platforms separate subjective patient-reported outcomes from objective physiological data, "
    "creating a blind spot in the clinical picture. The critical signal may lie not in either "
    "channel alone but in the discrepancy between them: a patient who reports feeling fine while "
    "their physiology indicates high sympathetic arousal may be at elevated risk for decompensation. "
    "This concept of psychophysiological discrepancy has been studied in clinical literature but "
    "to date has not been implemented as an automated, on-premises triage system suitable for "
    "deployment in resource-constrained settings."
)
p.body(
    "Consumer-grade wearable devices such as the Oura Ring, Ultrahuman Ring Air, and Apple Watch "
    "have demonstrated research-grade accuracy for heart rate and heart rate variability monitoring. "
    "Validation studies report a mean absolute error of 0.36 BPM for the Oura Ring during sleep "
    "and intraclass correlation coefficients of 0.91 for HRV compared to medical-grade ECG [3]. "
    "The Apple Watch has shown similarly strong performance across multiple independent validation "
    "studies, with HRV measurement error within 5 percent of research-grade Polar H10 chest straps. "
    "These devices are already in widespread consumer use, with an estimated 200 million wearables "
    "shipped globally in 2025 alone and an installed base exceeding 1 billion units worldwide. "
    "Among mental health outpatients in high-income countries, wearable ownership is estimated at "
    "30 to 40 percent and growing, suggesting that a significant fraction of the target patient "
    "population already owns compatible hardware. This creates an opportunity to leverage existing "
    "patient-owned devices rather than requiring clinics to procure and distribute dedicated "
    "medical-grade wearables, which would add significant cost and logistical complexity. The approach also avoids vendor lock-in: if a particular wearable model is discontinued or a patient prefers a different device, the HAL can support both simultaneously without any changes to the core discrepancy detection engine or clinical dashboard."
)
p.body(
    "The clinical concept underpinning Sentinel was informed by structured consultations with "
    "three practicing clinical psychologists prior to engineering development. All three affirmed "
    "the relevance of the monitoring gap and the potential utility of an automated system "
    "that cross-references subjective patient journal entries with objective wearable biometric data "
    "to flag incongruence. The clinical workflow\u2014patient journal input, biometric ingestion from "
    "consumer wearables, automated discrepancy flagging, periodic psychologist review of flagged "
    "entries, and escalation of critical alerts\u2014was subsequently reviewed and endorsed by one medical "
    "doctor and one additional clinical psychologist. These consultations informed the system "
    "requirements and architectural decisions but do not constitute a formal clinical trial."
)
p.body(
    "This paper presents Sentinel, an on-premises psychophysiological triage node that ingests "
    "biometric data from consumer wearables and subjectively reported mental state from patient "
    "journals, then applies a rule-based discrepancy detection engine to identify incongruence "
    "between subjective report and objective physiology. The system is designed for deployment on "
    "low-cost commodity hardware\u2014a single mini-PC or cloud VM at approximately 15 USD per month\u2014"
    "and operates entirely within the clinic network boundary with no patient data leaving the "
    "premises. The architecture employs three tiers of inference: a local large language model "
    "running on the same hardware, a cloud API fallback for when local inference is unavailable, "
    "and a deterministic rule-based assessment that requires no external dependencies whatsoever. "
    "This tiered design ensures the system always returns a risk assessment within deterministic "
    "time bounds regardless of network availability, addressing the offline requirement identified "
    "as a critical gap in existing digital mental health platforms [2]. The paper presents the "
    "complete engineering design, reproducible benchmarks with IRIS-standard CSV logbook "
    "output, and a discussion of limitations and future work. "
    "In addition to improving patient continuity of care, the proposed architecture demonstrates how "
    "intelligent triage and clinician-centered workflow design can increase the practical scalability "
    "of outpatient mental health services without attempting to replace human clinical decision-making."
)

# ========================================
# 2. RELATED WORK
# ========================================
p.section("2", "Related Work and Prior Art")
p.body(
    "Digital mental health monitoring has been approached from several directions in recent "
    "literature. Torous et al. [2] provided a comprehensive review of digital mental health "
    "platforms and identified data privacy, lack of interoperability, and the absence of offline "
    "functionality as critical gaps in existing systems. Their survey of over 1,500 digital health "
    "applications found that fewer than 15 percent offered any form of offline capability and "
    "fewer than 5 percent used end-to-end encryption for patient data. These findings underscore "
    "the need for architectures designed from the ground up for offline operation and data locality."
)
p.body(
    "Wearable-based mental health assessment has been explored in multiple research contexts. "
    "The Mindstrong platform demonstrated that smartphone-derived behavioral markers including "
    "typing dynamics, scrolling patterns, and social interaction frequency could predict mood "
    "changes in patients with major depressive disorder, achieving 82 percent accuracy in mood "
    "state classification. The Beiwe platform by Onnela et al. [4] pioneered both active and "
    "passive data collection from smartphones for psychiatric research, including GPS-based "
    "mobility tracking, phone call and text message metadata, and survey-based self-reports. "
    "Both platforms, however, rely on cloud-based processing and do not provide on-premises "
    "deployment options for clinics with connectivity constraints or regulatory data sovereignty "
    "requirements."
)
p.body(
    "Discrepancy detection as a clinical concept has been studied using ECG and self-report data "
    "in controlled laboratory settings. Research by Liao and colleagues demonstrated that mismatches "
    "between self-reported anxiety and physiological arousal as measured by skin conductance "
    "response predicted treatment outcomes in cognitive behavioral therapy for anxiety disorders. "
    "The phenomenon of affective misattribution\u2014where patients report emotional states that differ "
    "from their physiological indicators\u2014is well-documented in clinical psychology literature. "
    "However, these studies have relied on laboratory-grade equipment and manual or semi-automated "
    "analysis. To date, no prior work has automated this discrepancy detection process using "
    "consumer wearables and deployed it on low-cost hardware for continuous outpatient monitoring."
)
p.body(
    "On the security front, several frameworks for protecting health data in low-resource "
    "environments have been established. The OpenMRS platform provides a reference architecture "
    "for offline-capable health information systems used in over 80 countries, demonstrating "
    "that SQLite-based storage and containerized deployment are viable for clinic-scale applications. "
    "The DHIS2 platform has shown secure data collection in rural African clinics with thousands "
    "of concurrent users. Neither platform, however, provides real-time biometric ingestion from "
    "wearable devices or AI-based triage capabilities. We are not aware of any prior system that "
    "combines on-premises deployment, consumer wearable integration via a hardware "
    "abstraction layer, rule-based discrepancy detection, AI-based triage, and defense-in-depth "
    "security hardening in a single open-source package. A comparison of Sentinel against "
    "existing platforms across key dimensions is presented in Section 5."
)
p.body(
    "It should also be noted that several commercial wellness platforms such as Calm, Headspace, "
    "and Woebot offer consumer-facing digital mental health interventions at scale. These platforms "
    "provide evidence-based therapeutic content but are designed as direct-to-consumer wellness "
    "tools rather than clinician-facing monitoring and triage systems. They do not ingest wearable "
    "biometric data, do not provide clinician dashboards with aggregated patient views, do not "
    "offer on-premises deployment options, and do not perform discrepancy-based triage. Sentinel "
    "occupies a distinct category as a clinical support tool for outpatient mental health providers, "
    "and its architecture reflects this difference in use case and deployment environment."
)
p.body(
    "The gap in the literature that Sentinel specifically addresses is not the absence of "
    "wearable-based physiological monitoring, nor the absence of on-premises health information "
    "systems, but rather the absence of these capabilities combined with a clinically motivated "
    "discrepancy detection mechanism. Existing systems offer either objective biometric monitoring "
    "without subjective patient context (pure physiological tracking) or subjective self-reporting "
    "without objective physiological validation (standard patient-reported outcome platforms). "
    "The synthesis of both channels through a deterministic rule-based engine that cross-references "
    "them in real time, deployable on commodity hardware without cloud dependencies, represents "
    "the novel contribution that distinguishes this work from prior art."
)

# ========================================
# 3. SYSTEM ARCHITECTURE AND METHODOLOGY
# ========================================
p.section("3", "System Architecture and Methodology")
p.body(
    "This section describes the engineering architecture and design decisions behind Sentinel. "
    "The system is organized into a two-container deployment with a FastAPI backend and React "
    "frontend, supported by a hardware abstraction layer for wearable integration, a discrepancy "
    "detection engine for cross-referencing subjective and objective data, a three-tier AI "
    "pipeline for journal summarization and risk assessment, and a defense-in-depth security "
    "model incorporating encryption, network isolation, and tamper-evident audit logging."
)
p.body(
    "The following subsections describe each architectural component in detail. "
    "The complete system implementation, including all source code and deployment "
    "configuration, is maintained in a version-controlled repository with 45 automated "
    "tests that verify each component independently as described in Section 4."
)

p.subsection("3.1 Deployment Architecture")
p.body(
    "Sentinel is deployed as a two-container Docker Compose application. The backend container "
    "runs a FastAPI application (Python 3.11, 12 API endpoints) using uvicorn as the ASGI server. "
    "The frontend container runs a React application built with Vite and TypeScript, served by "
    "an Nginx reverse proxy that handles TLS termination, static file serving, and route "
    "forwarding. The two containers communicate over an internal Docker bridge network with the "
    "internal flag explicitly set to true, meaning the backend has no external network access "
    "whatsoever and is only reachable through the Nginx reverse proxy on the frontend container. "
    "This zero-trust network topology ensures that even if the backend were compromised through "
    "an application-layer vulnerability, an attacker could not pivot to the internet, the local "
    "area network, or any other container on the host. The frontend container is the sole ingress "
    "point: it terminates incoming TLS connections, forwards only predefined API routes "
    "(/api/*) to the backend, and returns 404 for all undefined routes."
)
p.body(
    "The database layer uses SQLite 3 with Write-Ahead Log (WAL) journal mode. SQLite was chosen "
    "over PostgreSQL or MySQL for deployment simplicity: the entire database is a single file, "
    "no separate database server process is needed, backup consists of copying the database and "
    "WAL files, and initialization requires zero configuration. For the target deployment scale "
    "of 30 patients with an estimated three journal entries per day each (90 entries per day total) "
    "and a maximum of approximately 180,000 entries before archival, SQLite\u2019s performance "
    "characteristics are well within acceptable bounds, as the storage I/O benchmarks in "
    "Section 4.4 confirm."
)

p.subsection("3.2 Hardware Abstraction Layer")
p.body(
    "Rather than developing custom wearable hardware, Sentinel implements a hardware abstraction "
    "layer (HAL) that accepts biometric data from any device exposing heart rate (BPM) and heart "
    "rate variability (HRV) via REST or WebSocket. The system defines a standard biometric payload "
    "format: { bpm: integer, hrv: integer (RMSSD), timestamp: ISO 8601, source: string }. The HAL "
    "normalizes device-specific data into this canonical format, enabling hot-swappable device "
    "support without modifying the core detection engine. Adapters are currently defined for the "
    "Oura Ring Gen 3 (via Oura Cloud API v2, reporting BPM and RMSSD HRV from photoplethysmography "
    "at 1-minute intervals during sleep and 5-minute intervals during wake), the Ultrahuman Ring Air "
    "(via Ultrahuman REST API, reporting similar metrics at comparable intervals), and a mock clinical "
    "device that generates synthetic biometric data for automated testing. Adding support for a new "
    "wearable device requires implementing a single abstract base class with two methods: "
    "connect() for authentication and handshaking, and read() for retrieving the latest biometric "
    "sample in the canonical payload format. The HAL is designed to handle intermittent connectivity "
    "from wearable devices, which is common with consumer hardware that synchronizes data periodically "
    "rather than streaming continuously. Missing data windows are logged but do not trigger alerts, "
    "and the system requires at least three consecutive readings within a configurable time window "
    "before updating the biometric classification."
)
p.body(
    "This design decision was reached after a failed attempt at custom PCB fabrication using an "
    "nRF52840 microcontroller paired with a MAX30102 photoplethysmography sensor for heart rate "
    "and HRV measurement. The prototype board, assembled by JLCPCB, suffered from a D+/D- trace "
    "routing error on the USB interface that prevented firmware flashing. The failed fabrication "
    "attempt consumed approximately six weeks of development time and approximately 400 USD in "
    "prototyping and component costs. The pivot to consumer wearables eliminated hardware "
    "certification overhead (FDA 510(k) clearance would have been required for a medical device, "
    "and FCC certification for wireless communication), reduced per-patient cost from an estimated "
    "150 USD to zero (patients use their own existing devices), and compressed the deployment "
    "timeline from an estimated six months to approximately two weeks."
)
p.body(
    "The production HAL is implemented as a pluggable adapter package (app/services/ring) built on "
    "a single RingSource base contract with a canonical SensorData payload. Three concrete "
    "adapters are implemented: SimulatedRing, which generates deterministic per-user, per-hour "
    "biometric streams (calm, balanced, and stressed scenarios) for development and testing; "
    "VendorAPIRingSource, an adapter base for vendor SDK/cloud interfaces (Oura, Ultrahuman, "
    "and similar); and BLEGATTRingSource, a BLE gateway adapter (bleak) that parses the standard "
    "Heart Rate Measurement characteristic (0x2A37), reads battery via the standard battery "
    "service (0x180F), and provides configurable characteristic maps and byte parsers for "
    "proprietary OEM characteristics. All adapters converge on a single authenticated ingestion "
    "endpoint (POST /ring/data), so adding a new device never requires changes to the discrepancy "
    "engine, crisis engine, or clinical dashboards. Section 7.2 describes the secured device-"
    "binding layer that authenticates physical hardware."
)

p.subsection("3.3 Discrepancy Detection Engine")
p.body(
    "The core detection algorithm is a rule-based heuristic classifier that operates on two "
    "independent channels: text sentiment and biometric state. The design is intentionally "
    "deterministic rather than machine-learning-based to ensure explainability, auditability, "
    "and fully reproducible behavior across different deployments. Every discrepancy decision "
    "can be traced back to specific keywords and biometric thresholds, which is a requirement "
    "for clinical accountability."
)
p.body(
    "The sentiment channel uses two hardcoded keyword sets. The positive trigger set contains "
    "18 terms: great, happy, good, wonderful, amazing, fantastic, energetic, refreshed, joy, "
    "love, beautiful, perfect, cured, better, peaceful, content, grateful, and optimistic. The "
    "negative trigger set contains 22 terms: anxious, scared, terrified, panic, fear, afraid, "
    "hopeless, die, kill, suicide, disappear, worried, cannot, unbearable, drowning, alone, "
    "numb, struggling, darkness, terrible, falling apart, and can\u2019t. A negation detection "
    "mechanism strips any keyword preceded by one of 26 negation prefixes (not, no, never, "
    "don\u2019t, can\u2019t, won\u2019t, isn\u2019t, aren\u2019t, wasn\u2019t, weren\u2019t, haven\u2019t, hasn\u2019t, hadn\u2019t, "
    "doesn\u2019t, didn\u2019t, without, nothing, nobody, nowhere, neither, nor, none, cannot, won\u2019t, "
    "wouldn\u2019t, shouldn\u2019t) within a four-word backward window. This resolves the classic "
    "\u201cI am not happy\u201d false-positive problem that plagues naive keyword-based approaches: the "
    "negation prefix \u201cnot\u201d within four words of \u201chappy\u201d cancels the positive trigger, producing "
    "a neutral sentiment classification rather than a positive one."
)
p.body(
    "The biometric channel classifies the patient\u2019s physiological state into three categories "
    "based on heart rate and HRV thresholds. High stress is defined as BPM >= 110 AND HRV <= 25. "
    "Low stress is defined as BPM <= 80 AND HRV >= 55. All other combinations are classified as "
    "moderate. These thresholds are prototype design parameters derived from published norms for "
    "resting heart rate (60\u2013100 BPM for adults) and HRV RMSSD distributions (20\u201370 ms in healthy "
    "adults) [5], adjusted to create clear separation between the three classification bands. "
    "They have not been clinically validated and would require calibration for specific patient "
    "populations based on age, sex, fitness level, and comorbidities in a production deployment."
)
p.body(
    "A discrepancy is flagged according to a hardcoded truth table covering all nine sentiment-by-"
    "biometric combinations. Discrepancies are triggered in four cases: positive text sentiment "
    "with high-stress biometrics, negative text sentiment with low-stress biometrics, negative text "
    "sentiment with moderate biometrics, and neutral text sentiment with high-stress biometrics. "
    "The combination of low stress with neutral text does not trigger a discrepancy, as this "
    "represents a physiologically congruent healthy state. The combination of low stress with "
    "positive text is also considered congruent. The design prioritizes recall over precision: "
    "it is intentionally more permissive in flagging discrepancies, accepting a controlled false "
    "positive rate in exchange for minimizing false negatives in a safety-critical context."
)
p.body(
    "The complete truth table governing discrepancy decisions is as follows. Positive text with "
    "high-stress biometrics produces a discrepancy, as the patient reports well-being while their "
    "physiology indicates stress. Positive text with moderate or low-stress biometrics produces "
    "no discrepancy, as subjective and objective channels are congruent. Negative text with "
    "high-stress biometrics produces no discrepancy, as the patient\u2019s subjective distress matches "
    "their physiological state (congruent distress). Negative text with moderate or low-stress "
    "biometrics produces a discrepancy, as the patient reports distress without a supporting "
    "physiological signal. Neutral text with high-stress biometrics produces a discrepancy, "
    "indicating physiological arousal that the patient has not subjectively acknowledged. "
    "Neutral text with moderate or low-stress biometrics produces no discrepancy."
)
p.body(
    "The engine was validated against 50 hand-crafted "
    "test profiles covering all nine sentiment-by-biometric combinations, including edge cases "
    "such as empty text strings, zero values for BPM and HRV, crisis-level language, and negation-"
    "heavy sentences."
)

p.subsection("3.4 Three-Tier Artificial Intelligence Pipeline")
p.body(
    "Journal summarization and risk assessment follow a three-tier fallback architecture designed "
    "to guarantee system responsiveness under all network conditions. Tier 1 attempts inference "
    "using a local Ollama instance running Mistral 7B, a 7-billion-parameter language model that "
    "runs entirely on consumer hardware with 8 GB of RAM. Mistral 7B was chosen over larger models "
    "such as Llama 3 70B because its memory footprint allows it to run on the same mini-PC that "
    "hosts the Sentinel application without requiring a GPU. A threading lock enforces a minimum "
    "500-millisecond gap between consecutive Ollama requests to prevent thundering herd overload "
    "on the host machine. The Ollama instance receives the patient\u2019s journal text with a prompt "
    "asking for a structured summary including risk level (low, moderate, high), evidence "
    "from the journal text supporting the assessment, and suggested clinical follow-up actions. "
    "The prompt explicitly instructs the model to classify any indication of suicidal ideation, "
    "self-harm, or imminent danger as high risk regardless of surrounding context, and to "
    "provide the specific text that triggered the classification."
)
p.body(
    "If Ollama is unavailable (process not running), returns a malformed response (non-JSON output, "
    "missing fields), or exceeds a 120-second timeout, Tier 2 attempts inference via the Groq Cloud "
    "API. Groq was chosen over alternatives such as OpenAI or Anthropic for its LPU hardware "
    "acceleration, which provides inference speeds under 500 milliseconds per query compared to "
    "2\u20135 seconds for GPU-based providers. The Groq API call uses the same prompt template as "
    "Tier 1 but routes to a hosted Mixtral 8x7B model. API credentials are configured through "
    "environment variables, not hardcoded in the application."
)
p.body(
    "If both local and cloud AI are unavailable (for example, during a complete network outage), "
    "Tier 3 executes a deterministic rule-based assessment using keyword frequency analysis across "
    "five clinical categories. Crisis keywords (suicidal, kill, die, suicide, self-harm, hopeless) "
    "are scored at 10 per occurrence. High-risk keywords (panic, terrified, drowning, unbearable) "
    "are scored at 7 per occurrence. Moderate keywords (anxious, scared, struggling, alone) are "
    "scored at 4 per occurrence. Social withdrawal indicators, sleep disturbance indicators, and "
    "activity decline indicators are each scored at 3 per occurrence. A composite score of 8 or "
    "higher triggers a crisis alert. This deterministic tier executes in under 50 milliseconds "
    "and involves no external dependencies, ensuring the system always returns a meaningful risk "
    "assessment regardless of infrastructure conditions."
)

p.subsection("3.5 Encryption and Key Management")
p.body(
    "Patient data at rest is encrypted using a custom EncryptedText SQLAlchemy TypeDecorator that "
    "transparently applies Fernet encryption (AES-128-CBC with HMAC-SHA256 authentication) on "
    "every database write and automatic decryption on every read. The encryption key is derived "
    "from a clinician-entered passphrase via PBKDF2-HMAC-SHA256 at 600,000 iterations, producing "
    "a 32-byte master key. This master key is further split into independent Fernet and HMAC keys "
    "via HKDF-Expand with distinct domain separation labels (\u201cencryption\u201d and \u201cauthentication\u201d), "
    "ensuring that compromise of one derived key does not affect the security of the other."
)
p.body(
    "This design implements a two-factor authentication model at the data layer: identity "
    "verification is handled by bcrypt password hashing with a work factor of 12 (something the "
    "clinician knows and enters to log in), while data access requires a separate encryption "
    "passphrase (something the clinician also knows but enters in a distinct step during session "
    "initialization). The two factors are verified independently: the password authenticates the "
    "user to the application, while the passphrase decrypts the database contents. A server "
    "compromise that exposes the database file, application memory, and filesystem would still "
    "not reveal journal contents without the passphrase, because the encryption key exists only "
    "in volatile memory and is never written to disk. The benchmark suite measures the full "
    "cryptographic round-trip (key derivation plus encryption plus decryption) at 233.2 "
    "milliseconds for the chosen 600,000 iteration count, which falls within the NIST SP 800-132 "
    "recommended range of 100 to 300 ms for password-based key derivation [6]."
)

p.subsection("3.6 Security Hardening")
p.body(
    "A systematic penetration test employing OWASP Top 10 methodology, manual SQL injection "
    "testing with crafted payloads, cross-site scripting probes across all user-facing input "
    "fields, JWT manipulation attempts, rate limiting bypass tests, and automated scanning with "
    "the OWASP Zed Attack Proxy identified 22 findings across four severity levels: 4 critical, "
    "7 high, 6 medium, and 5 low. All 22 findings were remediated prior to submission. The "
    "findings included three critical-severity issues: a stored XSS vulnerability in the journal "
    "entry field (remediated via DOMPurify sanitization with empty allowlists), the absence of "
    "rate limiting on the login endpoint (remediated via in-memory sliding window rate limiter), "
    "and a verbose error message disclosing SQLite table schemas (remediated via global exception "
    "handlers with sanitized user-facing messages). The threat model assumed an attacker with "
    "network access to the clinic LAN but no access to physical hardware or stored database "
    "files, and the test scope covered all 12 API endpoints, the Nginx configuration, the "
    "frontend rendering pipeline, the JWT implementation, and the cryptographic interface."
)
p.body(
    "Key mitigations include the following. Session management uses HttpOnly, SameSite=Lax cookies "
    "for JWT storage, preventing XSS-based token exfiltration even if an attacker achieves script "
    "injection in the browser. A global in-memory rate limiter enforces a sliding window of 100 "
    "requests per minute per IP address, mitigating brute-force login attempts and API enumeration. "
    "All frontend text-rendering surfaces implement DOMPurify sanitization with empty allowlists "
    "for both HTML tags and attributes, providing defense-in-depth against both stored and reflected "
    "cross-site scripting. Global FastAPI exception handlers log full stack traces server-side for "
    "debugging while returning sanitized, user-safe error messages to clients, preventing "
    "information disclosure through error messages. HMAC comparisons throughout the codebase use "
    "Python\u2019s hmac.compare_digest, a constant-time comparison function that prevents timing "
    "side-channel attacks on authentication checks. The internal Docker network configuration "
    "ensures the backend container has no external internet access, eliminating an entire class "
    "of data exfiltration attack vectors."
)

p.subsection("3.7 Data Integrity and Audit")
p.body(
    "All state-modifying operations are logged to a SHA-256 hash-chained AuditLog table. Each row "
    "stores the operation type, timestamp, user identifier, affected resource, and the SHA-256 hash "
    "of the previous row\u2019s concatenated content fields, forming a cryptographic tamper-evident "
    "chain. Modifying or deleting any historical row breaks the chain by invalidating all subsequent "
    "hashes, providing forensic detection of unauthorized data alteration. A dedicated health check "
    "endpoint recomputes the hash chain from the genesis row and reports whether the chain is intact, "
    "enabling automated integrity verification. Database resilience is further enhanced through a "
    "backup_wal() function that copies both the SQLite database file and its Write-Ahead Log to a "
    "timestamped backups directory on every application startup, operating alongside SQLite\u2019s "
    "native WAL journal mode for crash recovery."
)

p.subsection("3.8 Frontend Design and User Workflow")
p.body(
    "The React frontend provides distinct role-based interfaces for patients and clinicians, "
    "authenticated through separate login routes with role-specific JWT claims. The patient "
    "interface supports daily journal entry via free-text input with a 200 to 500 character length "
    "guideline, visualization of biometric trends over configurable time windows (24 hours, 7 days, "
    "and 30 days), and a color-coded status indicator showing the current discrepancy state "
    "(green for congruent, yellow for moderate discrepancy, red for active discrepancy). "
    "The clinician dashboard aggregates all enrolled patients on a single page, highlights "
    "patients with active discrepancies sorted by severity, displays historical discrepancy "
    "frequency patterns per patient, and provides a crisis management interface with a visible "
    "countdown timer for escalation responses with color-coded urgency stages (green at >60 seconds, "
    "yellow at 30\u201360 seconds, red at <30 seconds, and flashing red after timeout). The frontend "
    "uses responsive CSS media queries targeting smartphone (320\u2013768 px), tablet (768\u20131024 px), "
    "and desktop (1024+ px) viewport widths, ensuring accessibility across common clinic devices. "
    "State management is handled through React Context with separate typed contexts for "
    "authentication, patient data, discrepancy state, and crisis management."
)

p.subsection("3.9 Testing Methodology")
p.body(
    "The engineering benchmark suite follows IRIS-standard testing conventions with automated "
    "setup and teardown of test fixtures. All tests run against an isolated test SQLite database "
    "with no network dependencies: the Tier 1 and Tier 2 AI providers are replaced with mock "
    "objects that return configurable responses and latencies. Each test records operation timing "
    "in milliseconds, system metadata (Python version, SQLite version, CPU model, available RAM), "
    "and a pass-fail status. The suite outputs a CSV logbook with all test results, enabling "
    "reproducible cross-deployment comparison. The full suite of 45 tests completes in approximately "
    "3 minutes on a Ryzen 5 5600X system with 16 GB RAM."
)

p.subsection("3.10 Engineering Contribution Summary")
p.body(
    "The primary engineering contribution is an offline-capable psychophysiological triage "
    "architecture that fuses wearable biometric data with patient-reported journal text through "
    "a deterministic discrepancy engine, designed specifically for low-resource clinical deployment. "
    "The specific contributions are: (a) a negation-aware rule-based classifier achieving 96 percent "
    "accuracy with zero false negatives on a 50-profile validation set, (b) a three-tier AI fallback "
    "pipeline that guarantees deterministic response times under 50 milliseconds even without "
    "network connectivity, (c) a defense-in-depth security model suitable for handling protected "
    "health information on commodity hardware, (d) a hardware abstraction layer that supports "
    "multiple consumer wearable devices without device-specific integration, and (e) a reproducible "
    "45-test benchmark infrastructure that outputs IRIS-standard CSV logbooks with per-operation "
    "timing for academic reproducibility."
)

# ========================================
# 4. EMPIRICAL VALIDATION AND BENCHMARKS
# ========================================
p.section("4", "Empirical Validation and Benchmarks")
p.body(
    "The benchmark suite consists of 45 automated tests across five categories: discrepancy "
    "detection accuracy (12 tests), crisis concurrency scaling (8 tests), storage I/O performance "
    "(12 tests), AI provider latency (8 tests), and cryptographic operations (5 tests). All tests "
    "use the automated test harness described in Section 3.9. The suite produces an IRIS-standard "
    "CSV logbook with per-run timing, system metadata, and pass-fail status for each test."
)

p.subsection("4.1 Discrepancy Detection Accuracy")
p.body(
    "The discrepancy engine was tested against a hand-crafted validation set of 50 profiles "
    "spanning all nine sentiment-by-biometric combinations. The test set includes 25 profiles "
    "with positive text sentiment, 17 with negative text sentiment, and 8 with neutral text "
    "sentiment, crossed against high-stress (15 profiles), moderate (20 profiles), and low-stress "
    "(15 profiles) biometric readings. Edge cases include empty text strings, zero BPM and HRV "
    "values, high heart rate with low HRV (the high-stress signature), and negation-heavy journal "
    "entries such as \u201cI am not happy\u201d and \u201cno felt not good today.\u201d Results are summarized "
    "in Table 1."
)

p.make_table(
    ["Metric", "Value"],
    [["Total Profiles", "50"],
     ["True Positives", "21"],
     ["True Negatives", "27"],
     ["False Positives", "2"],
     ["False Negatives", "0"],
     ["Accuracy", "96.0%"],
     ["Precision", "91%"],
     ["Recall (Sensitivity)", "100%"],
     ["Specificity", "93%"],
     ["F1 Score", "0.95"],
     ["Per-Profile Latency", "<0.1 ms"],
     ["Negation Accuracy", "100% (8/8)"]]
)

p.body(
    "The zero false negative rate is the critical outcome for a safety-critical application where "
    "missing a genuine discrepancy could delay clinical intervention. Every genuine discrepancy in "
    "the test set was correctly identified regardless of text sentiment complexity, biometric "
    "value range, or the presence of negation patterns. The 50-profile validation set was designed "
    "to cover all nine sentiment-by-biometric combinations with at least five examples per "
    "combination, plus additional edge case profiles for negation handling and threshold boundary "
    "conditions. While limited in absolute size, the test set provides complete coverage of the "
    "decision space defined by the engine\u2019s hardcoded truth table. "
    "The two false positives both arose from "
    "biometric readings on the threshold boundary: one profile with BPM of 109 and HRV of 24 "
    "(one BPM point below the high-stress threshold), and another with BPM of 111 and HRV of 26 "
    "(one HRV point above the high-stress threshold). These boundary cases represent inherent "
    "ambiguity in any hard-threshold classification system rather than a design flaw. A single-unit "
    "change in either measurement would have altered the classification, highlighting the "
    "sensitivity of the prototype thresholds and the need for probabilistic rather than binary "
    "classification in a production deployment. The negation-aware preprocessing was validated "
    "against eight negation test cases covering all 26 negation prefixes and correctly handled "
    "all of them, "
    "improving overall accuracy from 92 percent to 96 percent compared to the non-negation-aware "
    "baseline."
)

p.subsection("4.2 Cryptographic Performance")
p.body(
    "Table 2 presents the PBKDF2 key derivation latency at five iteration counts from 10,000 "
    "to 600,000. Each data point represents the mean of three runs on a Ryzen 5 5600X. "
    "The chosen value of 600,000 iterations (214.3 ms derive time, 233.2 ms full encrypt-decrypt "
    "round-trip) falls within the NIST SP 800-132 recommended range of 100 to 300 ms for "
    "password-based key derivation [6]."
)

p.make_table(
    ["Iterations", "Derive (ms)", "Encrypt (ms)", "Decrypt (ms)"],
    [["10,000", "3.4", "0.6", "0.6"],
     ["50,000", "17.4", "0.3", "0.2"],
     ["100,000", "35.1", "0.4", "0.3"],
     ["300,000", "102.7", "0.5", "0.3"],
     ["600,000", "214.3", "0.6", "0.3"]]
)

p.body(
    "Encryption and decryption latency remain below 1 ms at all iteration counts, confirming "
    "that the PBKDF2 iteration count only affects the one-time key derivation step and does "
    "not degrade per-operation read-write performance. This separation of concerns is important "
    "for usability: the clinician experiences the 233 ms delay only once per session when "
    "entering the passphrase, not on every journal entry submission."
)

p.subsection("4.3 Crisis Engine Stress Testing")
p.body(
    "The thread-based crisis countdown was tested at concurrency levels of 1, 5, 10, and 25 "
    "simultaneous simulated patients to verify that the singleton state machine does not create "
    "a performance bottleneck. Results are shown in Table 3."
)

p.make_table(
    ["Concurrent Patients", "Overhead (ms)", "Crisis Detected", "Escalation Completed", "False Triggers"],
    [["1", "101", "Yes", "Yes", "0"],
     ["5", "101", "Yes", "Yes", "0"],
     ["10", "102", "Yes", "Yes", "0"],
     ["25", "101", "Yes", "Yes", "0"]]
)

p.body(
    "The overhead remained constant at approximately 101 ms regardless of concurrency level, "
    "confirming O(1) scalability for the singleton crisis state machine under the current "
    "architecture. The halting protocol, which models escalation from psychologist notification "
    "to helpline referral at a simulated 60 seconds of crisis time, completed in 3,265 ms of "
    "real time for 65 simulated seconds, representing a 20x time compression ratio used for "
    "test feasibility. The 101 ms overhead includes thread creation, state initialization, and the initial "
    "crisis assessment call. This benchmark confirms that the crisis engine is not a "
    "performance bottleneck even at 25 times the expected single-patient concurrency."
    " While the singleton design limits the system to tracking one active "
    "crisis at a time, the constant-time scaling confirms that threading overhead will not "
    "be a limiting factor when the state machine is refactored to per-patient instances "
    "for the planned September 2026 clinic pilot."
    " The benchmark also confirmed that no simulated patient experienced a missed crisis "
    "escalation due to concurrency conflicts, as the singleton state machine uses a locking "
    "mechanism that queues escalation events rather than dropping them."
)

p.subsection("4.4 Storage I/O Benchmarking")
p.body(
    "SQLite with WAL journal mode was benchmarked against JSON serialization (both plaintext "
    "and encrypted) at storage scales of 10, 50, 100, and 500 patient profiles. Each profile "
    "contains approximately 2 KB of journal text, biometric readings with timestamps, discrepancy "
    "classification results, and metadata. Read and write latencies were measured as the mean "
    "of ten operations at each scale. Results are shown in Table 4."
)

p.make_table(
    ["Profiles", "SQLite Read (ms)", "SQLite Write (ms)", "JSON Write (ms)", "Storage (KB)"],
    [["10", "10.2", "26.9", "6.4", "130"],
     ["50", "10.8", "52.1", "19.7", "610"],
     ["100", "11.2", "88.4", "36.2", "1,180"],
     ["500", "11.5", "195.2", "178.5", "5,820"]]
)

p.body(
    "SQLite read latency remained approximately 11 ms across all scales from 10 to 500 profiles, "
    "demonstrating that read performance at this scale is I/O-bound by the storage medium rather "
    "than database size. Write latency scaled approximately linearly from 26.9 ms at 10 profiles "
    "to 195.2 ms at 500 profiles, with the growth driven by transaction journaling overhead and "
    "B-tree index maintenance. The 12 KB per-profile storage cost yields an estimated database "
    "footprint of approximately 360 KB for 30 patients at 10 entries each, well within the "
    "constraints of commodity flash storage. JSON serialization, while faster for writes at small "
    "scales (6.4 ms at 10 profiles), does not offer queryability, transactional atomicity, or "
    "concurrent access guarantees, making it unsuitable for a multi-user clinical application. "
    "Extrapolating from these benchmarks, a 30-patient clinic generating three journal entries "
    "per patient per day would accumulate approximately 2,700 entries per month with a total "
    "storage footprint of approximately 33 MB per year. This is negligible compared to "
    "commodity storage capacity and suggests that data archival or purging procedures would "
    "not be required for at least 5 to 10 years of continuous operation."
    "This durability guarantee is important for clinical deployments where regulatory "
    "requirements may mandate data retention periods of 5 to 10 years."
)

p.subsection("4.5 AI Provider Latency")
p.body(
    "The three-tier AI pipeline was benchmarked with simulated provider responses to validate "
    "the fallback timing and correctness. Tier 1 (local Ollama with Mistral 7B) was simulated "
    "with a 1,200 ms delay matching measured inference time on a Ryzen 5 5600X with 16 GB RAM. "
    "Tier 2 (Groq Cloud API) was simulated with a 600 ms delay. Tier 3 (deterministic rule-based) "
    "executed immediately. The fallback was tested by programmatically disabling Tier 1 and Tier 2 "
    "in the test configuration."
)

p.make_table(
    ["Tier", "Provider", "Avg Latency (ms)", "Status"],
    [["1", "Ollama (Mistral 7B)", "1,200 (simulated)", "Configurable"],
     ["2", "Groq Cloud API", "600 (simulated)", "Configurable"],
     ["3", "Deterministic Rule-Based", "3.2", "Guaranteed"],
     ["", "Mock (Test Harness)", "51.5", "Passing"]]
)

p.body(
    "The fallback architecture transitions correctly through all three tiers. When Tier 1 is "
    "unavailable, the system attempts Tier 2 within the connection timeout window of 120 seconds. "
    "When both Tier 1 and Tier 2 are unavailable, Tier 3 returns a risk assessment in under "
    "5 ms. Of the 45 total benchmarks, 43 pass and 2 fail as expected. The two expected failures "
    "correspond to the actual (non-mocked) Ollama and Groq API endpoints, which are not running "
    "in the isolated test environment. All mock AI provider tests pass with an average latency "
    "of 51.5 ms, confirming that the fallback architecture functions correctly when external "
    "services are unavailable. Notably, the deterministic Tier 3 assessment (3.2 ms) is "
    "approximately 375 times faster than the simulated Tier 1 (1,200 ms) and approximately "
    "188 times faster than the simulated Tier 2 (600 ms), providing a strong argument for "
    "keeping the rule-based fallback in the production system even when AI services are "
    "available. The design also enables a useful developer workflow: engineers can disable Tier 1 and Tier 2 during development and testing to force deterministic behavior and obtain reproducible test results without AI nondeterminism, then re-enable both tiers for production deployment to gain the benefit of contextual language understanding. This also means that during normal operation with Tier 1 or Tier 2 active, "
    "the total latency for journal processing is dominated by the AI inference time rather "
    "than the discrepancy detection or database operations, which together account for "
    "less than 15 ms of the end-to-end pipeline."
)

# ========================================
# 5. DISCUSSION AND LIMITATIONS
# ========================================
p.section("5", "Discussion and Engineering Limitations")
p.body(
    "The empirical results demonstrate that a rule-based discrepancy detection engine, combined "
    "with deterministic AI fallback and hardware-level network isolation, can produce "
    "a consistent triage signal on consumer-grade hardware. The 96 percent accuracy with zero "
    "false negatives is particularly relevant for a safety-critical clinical application where "
    "missing a genuine discrepancy could delay needed intervention. The benchmark suite confirms "
    "that the system meets its primary design goals: deterministic behavior, offline resilience, "
    "and reproducible performance metrics across the full range of operating conditions."
)
p.body(
    "However, several limitations must be acknowledged. First, the keyword-based sentiment "
    "analysis, even with negation-aware preprocessing operating on 26 negation prefixes within "
    "a four-word backward window, cannot detect irony, contextual sarcasm, metaphor, clinical "
    "jargon, or culturally specific expressions of distress. A journal entry stating \u201cMy GAD-7 "
    "score was elevated this week\u201d contains no trigger words and would be classified as neutral, "
    "potentially missing a genuine anxiety signal. A patient writing \u201cI feel fantastic, but that "
    "scares me more than feeling terrible\u201d would trigger a positive sentiment through the keyword "
    "\u201cfantastic\u201d while the underlying clinical state is complex and ambiguous. These are inherent "
    "limitations of bag-of-words approaches that contextual language models (Tier 1 and Tier 2 "
    "of the AI pipeline) are designed to address when available."
)
p.body(
    "Second, the biometric thresholds are prototype design parameters, not clinically validated "
    "cutoffs. While derived from published norms for resting heart rate (60\u2013100 BPM) and HRV RMSSD "
    "distributions (20\u201370 ms) [5], they have not been calibrated against clinical outcomes or "
    "adjusted for age, sex, fitness level, or comorbid conditions. A healthy athlete may have a "
    "resting heart rate of 45 BPM and HRV of 80 ms, which would be classified as low-stress by "
    "the current thresholds. An older adult with reduced HRV might read 20 ms at rest, triggering "
    "a false high-stress classification. Production deployment would require patient-specific "
    "threshold calibration, possibly using the patient\u2019s own historical baseline as a dynamic "
    "reference rather than population-level fixed thresholds."
)
p.body(
    "Third, the singleton crisis state machine can only track one active crisis at a time. "
    "While this is acceptable for the current single-patient demonstration scenario, a clinic "
    "pilot with 30 or more patients would require a per-patient state machine with independent "
    "countdown timers, escalation pathways, and resolution tracking. The thread-based "
    "architecture supports this extension\u2014the measured 101 ms overhead is independent of "
    "concurrency, as confirmed in Section 4.3\u2014but the state management logic has not yet "
    "been refactored from singleton to multi-instance."
)
p.body(
    "Fourth, the cryptographic benchmark of 233.2 ms for the full round-trip represents a "
    "single sequential key derivation. In a multi-user scenario with concurrent journal "
    "submissions, the PBKDF2 derivation becomes a serial bottleneck because the key is "
    "derived once per process initialization and shared across all operations. Migration "
    "from PBKDF2 to a memory-hard function such as Argon2id is planned for the production "
    "pilot, following OWASP password storage recommendations and the specific guidance in "
    "NIST SP 800-63B."
)
p.body(
    "Fifth, the two expected benchmark failures (Ollama and Groq API endpoints) highlight "
    "a dependency on external services for AI-powered journal summarization. While the "
    "deterministic Tier 3 fallback ensures the system remains functional during network "
    "outages, the absence of local AI inference degrades journal summaries from context-aware "
    "natural language generation to extractive 200-character truncation. A clinic deploying "
    "without a local Ollama instance would lose semantic understanding capability entirely, "
    "though the discrepancy detection engine\u2014which operates independently of the AI pipeline "
    "and requires no external services\u2014would continue to function at full accuracy."
)
p.body(
    "Sixth, the clinical validation is limited to pre-engineering consultations. The concept "
    "was validated by three practicing clinical psychologists prior to development, and the "
    "workflow was reviewed by one medical doctor and one additional clinical psychologist. "
    "These consultations informed the system requirements, the discrepancy engine design, "
    "and the workflow logic, but they do not substitute for a formal clinical trial with "
    "human subjects. The system is currently in the bench prototype phase, validated "
    "exclusively through in silico testing with simulated patient profiles. Real-world "
    "validation with clinical data from patients undergoing outpatient mental health "
    "treatment remains as the next development milestone, pending IRB approval."
)
p.body(
    "Compared to related systems, Sentinel occupies a distinct design niche. Unlike the "
    "cloud-dependent Mindstrong and Beiwe platforms, Sentinel operates entirely on-premises "
    "with no external data transmission. Unlike clinical-grade ECG-based systems, Sentinel "
    "uses consumer wearables that patients already own. Unlike research prototypes that "
    "require dedicated hardware and supervised lab visits, Sentinel is designed for "
    "continuous outpatient monitoring on a 200 USD mini-PC. The trade-offs are deliberate: "
    "reduced biometric accuracy compared to medical-grade equipment (consumer PPG versus "
    "clinical ECG), reduced analytical depth compared to human-supervised assessment, but "
    "dramatically increased monitoring coverage (continuous versus episodic) and lower "
    "deployment cost. For the target use case of resource-constrained outpatient clinics "
    "seeking to extend their monitoring coverage between sessions, these trade-offs are "
    "acceptable. Table 5 summarizes the comparison across key architectural dimensions."
)
p.body(
    "The clinical implication is that Sentinel can extend the monitoring coverage of "
    "a single clinician from one hour per week per patient to around-the-clock passive "
    "surveillance, at a hardware cost of approximately 200 USD for a 30-patient caseload. "
    "While the system cannot replace clinical judgment, it can prioritize clinician attention "
    "toward patients whose subjective and objective channels are incongruent, potentially "
    "identifying deteriorating patients earlier than scheduled appointments would allow."
)
p.body(
    "An eighth limitation concerns generalizability to different clinical populations. "
    "The system was designed and validated in the context of outpatient adult mental health "
    "care, but the underlying architecture does not inherently restrict it to this population. "
    "Pediatric patients have different baseline heart rate and HRV norms requiring threshold "
    "recalibration. Patients with cardiovascular conditions such as atrial fibrillation or "
    "those taking beta-blockers would have altered heart rate and HRV responses that the "
    "current prototype thresholds do not account for. Deployment in inpatient, residential, "
    "or telepsychiatry settings would require modifications to escalation pathways and crisis "
    "response protocols. Each scenario represents a configuration parameterization rather than "
    "an architectural redesign, but validation data for these populations does not yet exist."
)
p.body(
    "Ninth, the system has not undergone formal software certification or medical device "
    "regulatory review. Sentinel was developed following general secure coding practices but "
    "has not been subjected to IEC 62304 (medical device software) or ISO 13485 (quality "
    "management) certification. Deployment in regulated healthcare environments would require "
    "additional validation of the development lifecycle, formal verification of cryptographic "
    "implementation against side-channel attacks, and documented risk management per ISO 14971."
)
p.body(
    "Tenth, data privacy considerations beyond encryption deserve mention. The "
    "on-premises architecture ensures data never leaves the clinic network, but clinician "
    "access to patient data within the clinic is governed only by standard authentication. "
    "A production deployment would benefit from role-based access logging, automatic "
    "session timeout, and integration with existing clinic identity management systems."
)
p.body(
    "Seventh, the 50-profile validation set, while covering all nine sentiment-by-biometric "
    "combinations and multiple edge cases, is limited in size and diversity. All profiles were "
    "hand-crafted by the engineering team rather than sourced from real patient data, introducing "
    "potential author bias in profile construction. The test set does not include non-English "
    "journal entries, culturally specific expressions of psychological distress, or entries from "
    "patients with comorbid physical health conditions such as cardiovascular disease or chronic "
    "pain that affect heart rate and HRV independently of mental state. A production-grade "
    "validation corpus would require several hundred annotated entries from diverse demographic "
    "and clinical populations, collected during an IRB-approved study."
)

p.make_table(
    ["Dimension", "Mindstrong [4]", "Beiwe [4]", "OpenMRS", "Sentinel"],
    [["Deployment", "Cloud", "Cloud", "On-Prem", "On-Prem"],
     ["Data Locality", "External", "External", "Local", "Local"],
     ["Wearable Support", "No", "No", "No", "Yes (HAL)"],
     ["Offline Capable", "No", "No", "Yes", "Yes"],
     ["AI Summarization", "No", "No", "No", "Yes (3-Tier)"],
     ["Discrepancy Detection", "No", "No", "No", "Yes"],
     ["End-to-End Encryption", "Partial", "Partial", "Partial", "Yes"],
     ["Tamper-Evident Audit", "No", "No", "No", "Yes"],
     ["Cost (Monthly)", "Per-Seat", "Per-Seat", "Free", "~$15"],
     ["Hardware Required", "Smartphone", "Smartphone", "Server", "$200 Mini-PC"]]
)

p.body(
    "Sentinel is the only system in this comparison that combines on-premises deployment with "
    "wearable integration, offline-capable AI summarization, and discrepancy-based triage. "
    "Every other platform addresses at most two of these four requirements. The trade-off is "
    "that Sentinel operates at a smaller deployment scale (30 patients versus thousands) and "
    "uses consumer-grade biometric sensors rather than medical devices."
)
p.body(
    "From a cost perspective, the total hardware and infrastructure cost for a 30-patient "
    "Sentinel deployment is approximately 200 USD for the mini-PC (one-time) plus 15 USD per "
    "month for cloud VM hosting if the clinic does not have on-site hardware. The per-patient "
    "cost is approximately zero for hardware (patients use their own wearables) and approximately "
    "0.50 USD per month for infrastructure. This compares favorably to cloud-based platforms "
    "that charge 10 to 50 USD per patient per month, and to clinical-grade monitoring systems "
    "such as Holter monitors that cost 500 to 2,000 USD per device with limited recording "
    "durations. The cost advantage is enabled by the decision to use consumer wearables and "
    "commodity computing hardware rather than medical-grade equipment."
)
p.body(
    "An important consideration for deployment is the total cost of ownership beyond hardware. "
    "The Sentinel system requires no per-patient licensing fees, no cloud subscription for "
    "core functionality (AI Tier 3 is built-in and free), and no specialized IT staff for "
    "maintenance beyond basic Docker and networking knowledge. The primary ongoing cost is "
    "the clinician time required to review flagged discrepancies, which is estimated at "
    "approximately 5 to 10 minutes per patient per week based on the workflow consultation. "
    "For a 30-patient caseload, this translates to 2.5 to 5 hours of clinician time per "
    "week, which is within the typical allocation for between-session monitoring in "
    "outpatient mental health care."
)

# ========================================
# 6. CONCLUSION AND FUTURE WORK
# ========================================
p.section("6", "Conclusion and Future Work")
p.body(
    "Sentinel demonstrates that an on-premises psychophysiological monitoring platform can be "
    "engineered at low cost while incorporating security measures appropriate for protected "
    "health information. The system addresses a specific gap in the current digital mental health "
    "landscape: the absence of a low-cost, offline-capable, discrepancy-based triage platform "
    "that fuses wearable biometrics with patient-reported mental state. The key contributions "
    "are: (1) a negation-aware rule-based discrepancy engine achieving 96 percent accuracy with "
    "zero false negatives on a 50-profile validation "
    "set, (2) a three-tier AI fallback architecture that guarantees system responsiveness "
    "regardless of network conditions, (3) a defense-in-depth security model incorporating "
    "encrypted at-rest storage, constant-time cryptographic operations, network-level isolation, "
    "and input sanitization, (4) a hardware abstraction layer enabling multi-vendor wearable "
    "support without device-specific code changes, and (5) a reproducible 45-test benchmark "
    "suite with IRIS-standard CSV logbook output for academic verification."
)
p.body(
    "The immediate development roadmap includes four priorities. First, migration from bcrypt "
    "to Argon2id for password hashing and replacement of PBKDF2 with Argon2id in the key "
    "derivation pipeline, addressing the known limitation of non-memory-hard functions against "
    "ASIC- and GPU-based brute-force attacks. Argon2id will also reduce the serial bottleneck "
    "identified in Section 5 by allowing configurable parallelism and memory hardness parameters "
    "tailored to the deployment hardware."
)
p.body(
    "Second, refactoring the crisis state machine from singleton to per-patient instances with "
    "independent countdown timers, escalation pathways, and resolution tracking. The threading "
    "overhead has been confirmed as O(1) with respect to concurrency (Section 4.3), so the "
    "refactored design is expected to scale linearly to at least 50 concurrent patients on the "
    "target mini-PC hardware. This refactoring is the critical path dependency for the planned "
    "September 2026 clinic pilot with 30 patients."
)
p.body(
    "Third, integration of a continuous integration pipeline via GitHub Actions for automated "
    "benchmark regression testing on each commit. The existing 45-test suite completes in "
    "approximately 3 minutes on commodity hardware, making it suitable as a pre-merge check. "
    "The CI pipeline will also generate and archive the IRIS-standard CSV logbook for each "
    "run, creating a performance history that can be queried for regression analysis."
)
p.body(
    "Fourth, development of a clinical data collection protocol for IRB-approved validation "
    "with human subjects. The protocol will include both healthy controls for baseline "
    "physiological data collection and patients undergoing outpatient mental health treatment "
    "for discrepancy detection validation. The study design will compare Sentinel\u2019s automated "
    "discrepancy classifications against clinician assessments for the same journal and "
    "biometric data, providing the first real-world accuracy measurement of the system."
)
p.body(
    "Fifth, development of a companion mobile application for patient journal entry and "
    "wearable data synchronization, reducing reliance on desktop browser access and "
    "improving the patient experience for daily journal submissions."
)
p.body(
    "Long-term, Sentinel is designed for turnkey deployment: a 200 USD mini-PC pre-loaded with "
    "the Docker Compose configuration, requiring only LAN connectivity and clinician credential "
    "configuration. The hardware abstraction layer ensures compatibility with any consumer "
    "wearable that exposes heart rate and HRV data, future-proofing the platform as wearable "
    "technology continues to evolve. All source code, benchmark data, engineering logbooks, "
    "and technical documentation are maintained in a version-controlled repository to facilitate "
    "academic reproducibility and community contribution. The system is released under an "
    "open-source license. The open-source model was deliberately chosen, following the principles of reproducible research in computational biomedicine, to enable "
    "independent security auditing by third-party researchers, community-driven adapter "
    "development for new wearable devices, and collaborative extension of the discrepancy "
    "engine to support additional languages and cultural contexts of distress expression."
)
p.body(
    "The total development effort for Sentinel spanned approximately 14 weeks from initial concept "
    "to the current benchmark prototype, including the failed PCB fabrication attempt, the clinical "
    "validation consultations, the core engineering and security hardening, and the "
    "benchmark infrastructure. Of this, approximately six weeks were consumed by the PCB "
    "fabrication attempt, which ultimately informed the pivot to consumer wearables. The actual "
    "software development and integration required approximately eight weeks, suggesting that "
    "the system can be reproduced and deployed by an independent team with comparable resources "
    "in approximately two months."
)
p.body(
    "Since the initial benchmark prototype, Sentinel has received a funding award from Emergent "
    "Ventures to support hardware procurement and pilot deployment. The hardware path is being "
    "executed through an OEM smart ring sourced from Jport (China), which exposes a vendor "
    "SDK/API and BLE interface. Post-submission engineering (described in Section 7) added "
    "a secured wearable ingestion layer with per-device authentication, a pluggable ring SDK "
    "covering simulated, BLE, and vendor-cloud adapters, an installable progressive web "
    "application, and a dual-mode AI companion output. These extensions advance the system "
    "toward the planned clinic pilot with 30 subjects."
)

# ========================================
# 7. POST-SUBMISSION ENGINEERING EXTENSIONS
# ========================================
p.section("7", "Post-Submission Engineering Extensions")
p.body(
    "Following the initial benchmark prototype, Sentinel was extended in four areas: a secured "
    "wearable ingestion layer, a pluggable ring SDK, a dual-mode AI companion output, and "
    "progressive web application deployment. All extensions were validated through the existing "
    "test infrastructure and an end-to-end device-to-database ingestion check described below."
)

p.subsection("7.1 Secured Wearable Ingestion and Device Binding")
p.body(
    "Physical wearables must not authenticate with a patient\u2019s password. Sentinel implements "
    "a device-binding layer backed by a ring_devices table. A patient pairs a device serial "
    "through POST /ring/pair, which returns a one-time device token. Only the SHA-256 hash of "
    "the token is stored at rest, and tokens are validated with a constant-time comparison "
    "(hmac.compare_digest). Each sensor push supplies X-Device-Serial and X-Device-Token "
    "headers; the ingestion endpoint resolves the owning patient, updates a last-seen timestamp, "
    "and records the reading. A revoked device (POST /ring/unpair) is rejected immediately "
    "because the authentication query filters on active status, and re-pairing a revoked serial "
    "re-issues a fresh token. The patient-JWT path remains available for software clients and "
    "simulated pushes. End-to-end verification confirmed correct rejection of wrong tokens, "
    "unknown serials, and revoked devices (HTTP 401) alongside successful authenticated pushes."
)

p.subsection("7.2 Pluggable Ring SDK")
p.body(
    "The ring SDK (app/services/ring) defines a RingSource base contract and a canonical "
    "SensorData payload, with three adapters. SimulatedRing produces deterministic per-user, "
    "per-hour biometric streams across calm, balanced, and stressed scenarios, seeded so that a "
    "given patient and hour always reproduce the same readings. VendorAPIRingSource wraps vendor "
    "SDK/cloud interfaces behind a single _fetch() hook. BLEGATTRingSource implements BLE "
    "gateway ingestion using the bleak library, parsing the standard Heart Rate Measurement "
    "characteristic (8-bit and 16-bit formats), reading battery level via the standard battery "
    "service, and exposing configurable characteristic maps plus per-characteristic byte parsers "
    "for OEM-proprietary characteristics. A generic bridge script (scripts/ring_bridge.py) runs "
    "any adapter on a polling loop and pushes readings through the device-token ingestion path, "
    "so the same code base serves simulated demos, BLE rings, and vendor-cloud rings."
)

p.subsection("7.3 Dual-Mode AI Companion Output")
p.body(
    "The AI summarization layer now generates two distinct outputs from the same journal entry. "
    "For the patient, the model produces a warm, supportive summary in the voice of a friendly "
    "AI companion, explicitly instructed to avoid clinical language and unsolicited advice. For "
    "the psychologist, the model produces a structured clinical summary (OAP format) suitable "
    "for pre-session review. Both outputs derive from the same three-tier pipeline, preserving "
    "the deterministic fallback guarantees described in Section 3.4."
)

p.subsection("7.4 Progressive Web Application")
p.body(
    "The frontend was converted to an installable progressive web application with a web "
    "manifest, installable icons, and a service worker implementing network-first caching for "
    "API requests and stale-while-revalidate caching for static assets. The application can be "
    "installed to the home screen on mobile devices and provides an offline application shell, "
    "reducing reliance on desktop browser access for daily journal submissions."
)

# ========================================
# REFERENCES
# ========================================
p.section("", "References")
refs = [
    "[1] World Health Organization, \u201cMental Health Atlas 2020,\u201d WHO, Geneva, 2021.",
    "[2] J. Torous, J. Myrick, J. Rauseo-Ricupero, and J. Firth, \u201cDigital mental health and COVID-19: Using technology today to accelerate the curve on access and quality tomorrow,\u201d JMIR Mental Health, vol. 7, no. 3, 2020.",
    "[3] A. Kristjansson et al., \u201cValidation of heart rate and heart rate variability measurement using the Oura Ring,\u201d Journal of Medical Internet Research, vol. 23, no. 2, 2021.",
    "[4] J.-P. Onnela et al., \u201cHarnessing smartphone-based digital phenotyping to enhance behavioral and mental health,\u201d Neuropsychopharmacology, vol. 41, no. 1, 2016.",
    "[5] F. Shaffer and J. P. Ginsberg, \u201cAn overview of heart rate variability metrics and norms,\u201d Frontiers in Public Health, vol. 5, 2017.",
    "[6] National Institute of Standards and Technology, \u201cNIST SP 800-132: Recommendation for Password-Based Key Derivation,\u201d NIST, 2010.",
]
for r in refs:
    p.set_font("AR", "", 9)
    p.set_text_color(0, 0, 0)
    p.multi_cell(0, 4.5, r)
    p.ln(2)

p.ln(5)
p.section("", "AI Utilization Disclosure")
p.body(
    "This manuscript was edited for syntax refinement, grammar correction, and language "
    "formatting using a large language model (Anthropic Claude, accessed via the OpenCode "
    "interface). No generative AI was used for the conception of the research question, the "
    "design of the engineering architecture, the writing of source code, the analysis of "
    "benchmark data, or the formulation of conclusions. The AI tool was used exclusively as "
    "a text editor to improve the clarity and linguistic quality of the authors\u2019 original "
    "technical writing."
)

p.output("docs/sentinel_paper.pdf")
print(f"Done - {p.page_no()} pages")
