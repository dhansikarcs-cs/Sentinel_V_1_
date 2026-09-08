# The Sentinel System: An Assistant for the Overloaded Clinician

## 1. The Problem — Buried, Not Absent

Mental health clinicians are not failing their patients; they are drowning. The people they are responsible for spend 167 of every 168 hours out of sight — mood shifts, distress, and early-warning signs build in those unseen hours and surface only at the next appointment, when the clinician is expected to already know. Yet there is no time to look. Documentation, journal review, and manual risk assessment consume hours every week; caseloads run far beyond safe limits (India runs 0.75 psychiatrists per 100,000 against a WHO recommendation of 1 per 10,000); and the emotional weight of carrying every patient's story compounds into secondary trauma and burnout. Existing tools add to the load rather than lightening it — telehealth is appointment-only, wellness apps are generic and disconnected from the clinical loop, and crisis helplines operate with no continuity of care. None of them reduce the clinician's actual work, and none unify patient, psychologist, and trusted contact in one real-time loop. Patients carry this cost directly: when no clinician can see the between-session hours, risk is discovered late and crises land without warning. The 167-hour gap is not a patient problem or a clinician problem — it is a system gap that both pay for.

## 2. The Sentinel Assistant

Sentinel is built around the clinician's day. It does the invisible work so the clinician can do the visible one — be present with patients. It is not another dashboard to check at the end of the day; it is work that does itself, so the end of the day is earlier. Four pillars make this possible.

**An assistant that reads everything.** Every journal entry is read, summarized, and classified across 28 GoEmotions emotion labels. Clinical notes are synthesized in OAP format. Silent periods are flagged. Echo detection stops the AI from parroting the patient's words back, and a TF-IDF emotion classifier runs locally in milliseconds. What once took hours of evenings now appears on the dashboard before the clinician arrives, and the AI never gets tired, never skips a patient, and never forgets a detail.

**A triage queue that thinks.** Only assigned patients appear, ranked by risk score, with crisis cases auto-expanded at the top. Cross-patient patterns and relapse indicators surface automatically. Bookings are managed with accept and waitlist, follow-up tasks are graded with one click, and encrypted session notes live per psychologist. The clinician walks in already knowing who needs them most — the sickest patient is never buried under paperwork.

**A crisis engine that never sleeps.** When a patient triggers a crisis, a staged protocol responds automatically without anyone needing to act: an immediate siren, a trusted-contact email with a signed acknowledgment link at 30 seconds, and helpline escalation at 60 seconds. The clinician halts it with one tap and the response timer freezes. The clinician is never the single point of failure — the system holds the line until a human arrives, and a trusted contact with a signed link can acknowledge from their phone in one tap.

**A guard against burnout.** Self-monitoring metrics surface the clinician's own stress, cumulative session load, and fatigue before secondary trauma sets in. The tool that watches over patients also watches out for the person watching them, because a system that burns out its clinicians fails its patients too.

## 3. Judgment Stays Human

The AI summarizes, triages, and alerts — it never diagnoses, prescribes, or overrides judgment. Every output is explainable and carries its model version, prompt version, and confidence score; an alert is never a black box. The clinician's decision is final, and nothing enters a clinical record without their approval. This design is deliberate: in mental health, the wrong inference can harm. By keeping the AI advisory and auditable, Sentinel protects both the patient and the professional. The assistant is not an extra screen; it is the time that comes back. Privacy is absolute: the AI runs fully offline via Ollama, so patient data never leaves the clinic, and cloud AI is disabled by default.

## 4. Scientific Foundation

The system rests on psychophysiological integration. The ring ingests heart rate, stress, sleep, and SpO₂ deterministically, and a discrepancy detector flags mismatches between body and text. Research shows physiological markers — elevated resting heart rate, disrupted sleep — often precede self-reported emotional deterioration by 24–48 hours. By presenting biometric trends alongside emotion-labeled journal language, Sentinel gives the clinician a cross-signal view: a patient writing "I'm fine" with an elevated heart rate and fear markers is not fine. The clinician sees the discrepancy in seconds instead of missing it for weeks.

## 5. Validation and Deployment

Sentinel passes 98/98 automated tests, reaches 96% discrepancy-detection accuracy at 0.1 ms, and ships a 47-run timing benchmark with crisis, storage, and inference measurements — all reproducible from the repository. Testing spans authentication, the journal pipeline, crisis triggering with cooldown, the risk engine, ring ingestion, and the event store, with frontend builds gated on TypeScript and Vite. Security includes bcrypt password hashing, rotating JWT sessions, rate limiting, a hash-chained audit log, and encrypted sensitive fields. The FastAPI + React stack with SQLAlchemy over SQLite (PostgreSQL-ready) runs on free-tier infrastructure at a $0 monthly operating cost, installs as a PWA on any device, and deploys to any clinic, school, or community center with zero financial barrier. A golden-set regression suite gates every change in CI, so the assistant the clinician trusts today is the same assistant tomorrow.

## 6. The Promise

Sentinel does not replace clinical judgment — it gives it back the time it lost. Hours of documentation each week return to the patient. A crisis safety net never sleeps, so no clinician carries the burden alone. A practice that once burned out its people can now protect them. The clinician gets an assistant; the patient gets a clinician who is present. Built over three years of independent research, it is already running today — the next step is a clinical pilot with a partner institution.
