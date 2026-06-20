# The Sentinel Ecosystem: Hardware-Software Infrastructure for Clinical Resilience

## 1. The Problem — A System Under Strain

Mental healthcare operates on a reactive model. Patients attend weekly sessions, but the remaining 167 hours between appointments are unmonitored. During this gap, crises develop, tasks go uncompleted, and patients feel isolated. Simultaneously, psychologists manage caseloads exceeding recommended limits — India's psychiatrist-to-population ratio is 0.75 per 100,000, compared to the WHO-recommended 1 per 10,000. The result is a dual failure: patients lack continuous support, and clinicians face burnout from administrative overload and secondary trauma.

Existing solutions fragment care. Telehealth platforms offer appointment-only access. Crisis helplines have wait times averaging 3–5 minutes. Wellness apps provide generic content without clinician integration. No platform connects patient, psychologist, and trusted contact in a unified real-time loop, and none integrate both physiological and emotional data streams for holistic assessment.

## 2. The Sentinel Ecosystem — Not a Project, an Infrastructure

Sentinel is designed as a hardware-software ecosystem, not a singular application. Its uniqueness lies in three architectural distinctions:

**Tri-directional stakeholder loop:** Sentinel simultaneously serves patients, psychologists, and trusted contacts through three synchronized interfaces — a patient self-monitoring portal, a clinician triage dashboard, and a no-login trusted contact response page. No existing platform connects all three in real-time with automated escalation.

**Hardware-software integration:** Biometric data from wearable-grade sensors feeds into the same assessment pipeline as emotional journal entries. This creates a unified psychophysiological data stream — heart rate variability, sleep patterns, and stress levels analyzed alongside subjective mood and written reflection.

**End-to-end workflow closure:** From crisis trigger to acknowledgment, from task assignment to graded feedback, from booking submission to status notification — every loop closes within the ecosystem.

### 2.1 Patient Portal

Users log daily journal entries with AI summarization (dual-mode: warm patient reflection + clinical OAP notes), daily mood emoji tracking locked per day with automatic reset, emotion classification across 28 GoEmotions labels (sadness, fear, nervousness, etc.) feeding into every summary, biometric trend visualization, session booking via dropdown of available dates, and one-tap crisis trigger with automatic activation when biodata and emotional trends indicate distress.

### 2.2 Psychologist Portal

Clinicians see only their assigned patients in a prioritized queue based on crisis status. They receive AI-synthesized clinical notes in OAP format, assign and grade follow-up tasks with proof-based completion, manage booking requests with accept/waitlist, and access encrypted session notes. The AI sidebar provides pre-session briefs, cross-patient pattern detection, and silent period monitoring.

### 2.3 Adaptive Smart Room — Shared Sensory Modulation

The smart room modulates visual (amber-to-cool lighting), acoustic (low-frequency pink noise, 60–200 Hz), and olfactory (lavender, vanilla) channels based on the physiological state of both the patient and psychologist simultaneously. When both occupants show elevated stress, the environment modulates for the dyad — creating a shared calming field that deepens therapeutic presence and models self-regulation.

This configuration is a foundational prototype. The ecosystem supports per-psychologist customization from a single biometric ring + web dashboard to a full sensory clinic room. Future iterations introduce plugin-based expansion for additional sensors and actuators.

### 2.4 Crisis Engine

When a patient triggers emergency: immediate audiovisual siren (0–29s), trusted contact email with acknowledgment link (30s), helpline escalation (60s). Psychologist acknowledgment at any stage stops all escalation and records resolution time.

## 3. AI as Assistant, Not Replacement

The AI never makes clinical decisions. It does not diagnose, prescribe, or override clinical judgment. Its role is strictly supportive. The custom `sentinel` model (7.2B parameters, therapy-tuned via Ollama) provides empathy-toned reflections for patients and structured clinical notes for psychologists. A TF-IDF emotion classifier over 28 GoEmotions labels detects emotional states from journal text, and echo detection prevents the AI from simply parroting the patient's words.

For clinics requiring absolute data privacy, the model runs entirely offline via Ollama — no data leaves the building. For cloud deployments, Groq API provides fast summarization as fallback. A three-tier fallback ensures resilience: Ollama → Groq → rule-based extraction.

## 4. Scientific Foundation — Biology Meets Psychology

Sentinel's assessment approach is rooted in psychophysiological integration:

- **Biometric data:** Heart rate, stress levels, sleep duration, SpO₂, mood — deterministically seeded per user per hour
- **Emotional data:** Free-text journals with emotion-labeled analysis across 28 labels
- **Emotion classifier:** TF-IDF + LogisticRegression trained on GoEmotions, running locally as a Python pickle (~4 MB)

Research demonstrates that physiological markers — elevated resting heart rate, disrupted sleep — often precede self-reported emotional deterioration by hours or days. By combining these streams with emotion-labeled analysis, Sentinel enables earlier pattern recognition.

## 5. Self-Care for the Clinician

The psychologist dashboard includes self-monitoring metrics, creating awareness of secondary traumatic stress and fatigue — promoting proactive self-care.

## 6. Accessibility & Deployment

The entire platform runs on free-tier services — Ollama (fully offline) or Groq AI, Streamlit, and Render.com. SQLite/PostgreSQL dual-backend replaces the earlier JSON storage with transaction-safe operations across 15 database tables (patient_profiles, journal_entries, mood_log, crisis_state, and more). Zero financial barrier for any clinic, school, or community center.
