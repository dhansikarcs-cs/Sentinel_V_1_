# The Sentinel Ecosystem: A Hardware-Software Infrastructure for Clinical Resilience

## 1. Introduction

The global mental health crisis presents a dual challenge rarely acknowledged in clinical systems design: patients require continuous, real-time support between therapeutic sessions, while clinicians face escalating burnout from caseloads that exceed sustainable limits. Current digital health solutions address one side in isolation — telehealth platforms offer appointment-only connectivity, wellness apps provide generic content without clinician integration, and crisis helplines operate as standalone services with no continuity of care. No existing platform unifies the patient, the psychologist, and the trusted contact into a single, real-time, privacy-preserving ecosystem, and critically, none integrate both physiological and emotional data streams with automated emotion classification for holistic clinical assessment.

This proposal presents the Sentinel Ecosystem — a hardware-software infrastructure designed not as a singular application but as a comprehensive clinical support system. Built on open-source foundations with zero-cost cloud services, Sentinel demonstrates that enterprise-grade mental health technology is achievable without enterprise budgets.

## 2. The Problem — A Symmetric Crisis

### 2.1 Patient Vulnerability Between Sessions

The therapeutic relationship is confined to weekly or biweekly appointments. In the intervening hours, patients experience emotional fluctuations, develop maladaptive patterns, and in critical cases, enter crisis states without a channel for immediate intervention. The absence of structured between-session support creates a treatment gap where therapeutic progress degrades and crises escalate undetected.

### 2.2 Clinician Overload and Burnout

The WHO reports a global median of 0.75 psychiatrists per 100,000 population in low-resource settings. Each clinician manages caseloads requiring continuous monitoring, documentation, triage, and intervention coordination. The administrative burden — reviewing journal entries, synthesizing session notes, tracking follow-ups, and manually assessing risk — consumes time that should be directed toward therapeutic presence.

### 2.3 The Trusted Contact Gap

Family members and close contacts of patients in distress are rarely integrated into the clinical workflow. When a crisis occurs, they are either uninformed or uncertain how to respond.

### 2.4 The Data Silos Problem

Patient data exists in separate silos. Biometric trackers record physiology. Journals capture subjective experience. Clinicians hold session notes. No system correlates these streams — leaving cross-signal patterns undetected until they manifest as crisis.

## 3. Why Sentinel Is Unique — An Ecosystem, Not a Project

Sentinel's uniqueness stems from three architectural distinctions:

**Tri-directional stakeholder loop.** Sentinel simultaneously serves three distinct user groups through synchronized interfaces — a patient self-monitoring portal, a clinician triage dashboard with real-time crisis awareness, and a no-login trusted contact response page. These share a SQLite/PostgreSQL state layer — a crisis triggered by the patient is instantly visible to the psychologist and simultaneously actionable by the trusted contact.

**Hardware-software integration.** Biometric data from wearable-grade sensors routes through the same assessment pipeline as emotional journal entries. Heart rate variability, sleep duration, stress levels, and SpO₂ are captured alongside subjective mood and written reflection enriched with emotion classification across 28 GoEmotions labels (sadness, fear, nervousness, anger, etc.) — enabling detection of discrepancies between what a patient feels and what their physiology and language show.

**End-to-end workflow closure.** Every clinical loop closes within the ecosystem. Crisis trigger leads to acknowledgment with frozen timer. Task assignment leads to proof upload and graded feedback. Booking submission leads to accept/waitlist notification. No external tools required.

## 4. The Sentinel Solution

Sentinel is a modular, dual-portal platform operating on a shared database layer with three integrated subsystems.

### 4.1 Patient Portal

The patient interface provides biometric trend visualization (BPM, stress, sleep, SpO₂, mood), AI-summarized journaling with daily mood emoji tracking locked per day and automatically resetting at midnight, emotion classification across 28 GoEmotions labels feeding into every AI summary, session booking via dropdown of available dates from the assigned psychologist, follow-up task management with proof-based completion, and a one-tap crisis trigger with automatic activation when biodata and emotional trends indicate distress.

### 4.2 Psychologist Portal

The clinician interface presents only their assigned patients in a triaged list where crisis cases auto-expand. AI-synthesized clinical notes (dual-mode: warm patient reflection for journals, OAP clinical format for session notes) replace manual documentation. A follow-up grading system allows structured feedback with 🟢🟡🔴 evaluation. The booking queue supports accept/waitlist workflows. An AI sidebar provides pre-session briefs per patient, cross-patient pattern detection, relapse indicators, and silent period monitoring. Encrypted clinical notes are segregated per psychologist. Self-monitoring metrics alert the clinician to their own stress and fatigue levels.

### 4.3 Trusted Contact Portal

A standalone page (no login required) allows designated contacts to receive crisis notifications, confirm acknowledgment, and indicate physical response ("I'm on my way"). The psychologist dashboard reflects this status in real time. Access is secured by a signed link (HMAC over the patient identity and an expiry window), so the page cannot be guessed, replayed, or repurposed for another patient.

### 4.4 Adaptive Smart Room — Shared Sensory Modulation

Sentinel extends beyond software into the physical therapy environment through an adaptive smart room that modulates sensory variables based on the physiological state of both occupants simultaneously.

**Visual modulation.** Lighting shifts between calming amber (2700K) during elevated sympathetic arousal and cool white (5000K) during cognitive engagement, following a gradual slewing algorithm below conscious perception.

**Acoustic masking.** Low-frequency pink/white noise (60–200 Hz) through surface transducers creates ambient vibration that masks environmental distractions and stimulates the vagal system via bone conduction.

**Olfactory integration.** Ultrasonic diffusers release calibrated concentrations of lavender and vanilla — shown in RCTs to lower state anxiety and reduce salivary cortisol.

**Co-regulation mechanism:** When both occupants show elevated stress, the environment modulates for the dyad — creating a shared calming field that deepens therapeutic alliance while modeling self-regulation for the patient.

**Modular architecture.** This is a foundational prototype supporting per-psychologist customization from a single biometric ring + dashboard to a full sensory clinic room.

## 5. Crisis Engine — Multistage Escalation Protocol

The crisis engine implements a time-sensitive escalation hierarchy:

- **Stage 1 (0–29 seconds):** Ambulance-style siren activates on the patient's device, providing immediate sensory feedback
- **Stage 2 (30 seconds):** Email notification to trusted contact with a signed acknowledgment link; contact can indicate they are en route
- **Stage 3 (60 seconds):** Helpline escalation email if no acknowledgment received
- **Termination:** Psychologist acknowledgment at any point stops all escalation, freezes the response timer, and records resolution duration

Activation is driven by an explainable risk engine (1–10) that blends keyword signals with emotion-classifier probabilities and a temporal trend over recent entries; automatic activation happens at the crisis threshold (≥8) and is throttled by a 3600-second cooldown so repeated journal entries cannot fire the full protocol repeatedly. This protocol ensures no crisis remains unaddressed due to a single point of failure.

## 6. AI as Assistant, Not Replacement

A critical design principle: AI supports, it does not decide. The system never diagnoses, prescribes, or overrides clinical judgment. Its functions are strictly supportive:

- **Journal summarization (patient mode):** Warm, empathetic reflection that validates feelings while explicitly avoiding any advice, suggestions, or coping techniques. Uses the custom `sentinel` Ollama model (7.2B parameters, therapy-tuned).
- **Clinical note synthesis (clinical mode):** Converts session observations into Observations, Assessment, and Plan format — reducing documentation time.
- **Emotion classification:** A TF-IDF + LogisticRegression pipeline trained on the GoEmotions dataset (28 labels) runs locally as a Python pickle (~4 MB), detecting emotional states from journal text before AI summarization. The detected emotions are passed as hints to the AI, improving summary accuracy.
- **Echo detection:** Prevents the AI from simply repeating the patient's raw words back as a "summary" by checking word overlap (>85% = echo → fallback path).
- **Trend flagging:** Identifies discrepancies between biometric data, emotion labels, and self-reported mood — as contextual information for the clinician, not as alarms.
- **Three-tier fallback:** Custom `sentinel` model (Ollama, local) → Groq Cloud API → rule-based extraction. Ensures AI never fails silently.

### 6.1 Privacy-First AI — Local Ollama Option

The custom `sentinel` model runs entirely on local hardware — no data leaves the local network, no third-party API is contacted, no internet connection required. For deployments where cloud AI is acceptable, Groq Cloud API provides fallback summarization with encrypted transport.

## 7. Scientific Foundation — Psychophysiological Integration

Sentinel's assessment architecture simultaneously captures two independent data streams:

### 7.1 Biometric Data Stream
Heart rate (BPM, 40-120), stress level (0-100%), sleep duration (3-10h), blood oxygen saturation (SpO₂, 90-100%), and categorical mood state — deterministically seeded per user per hour via seeded random generation.

### 7.2 Emotional Data Stream
Free-text journal entries capturing subjective experience, enriched by the emotion classifier producing GoEmotions 28-label analysis — detecting sadness, fear, nervousness, anger, grief, joy, surprise, and 21 other emotion categories.

### 7.3 The Integration Rationale

Research consistently demonstrates that physiological markers often precede self-reported emotional deterioration by 24-48 hours. By presenting biometric trends alongside emotion-labeled journal analysis, Sentinel enables clinicians to detect cross-signal patterns — a patient writing "I'm okay" while their biometric trend shows escalating stress and their language shows fear+sadness markers.

## 8. Workflow Systems

**Follow-up Tasks:** Psychologists assign tasks. Patients upload proof before marking complete. Psychologist grades as green/yellow/red with written feedback.

**Session Booking:** Patients select from available dates via dropdown. Psychologist accepts or waitlists. Real-time status notification to patient.

**Clinical Documentation:** Session notes encrypted per psychologist, with AI synthesis alongside original text. Mood entries logged daily per patient (one per day, upsert on conflict), locked after first selection, automatically resetting each day.

## 9. Technical Architecture

**Frontend:** React 19 + TypeScript 5.4 + Vite 6, installable as a PWA (web manifest, service worker with network-first API caching and offline app shell).

**Backend:** FastAPI 0.109 with SQLAlchemy 2.0 over SQLite (PostgreSQL-ready), connection-safe session management, and a module layout (`api → services → repositories → models`) that keeps route handlers away from models.

**Authentication:** bcrypt password hashing with a strict password policy (length, case, digits, specials, common-password blacklist), HS256 JWT access tokens with refresh-token rotation, HttpOnly cookie session storage, and per-account lockout after repeated failures. Sensitive fields are transparently encrypted with a PBKDF2-600K-derived Fernet key (encryption activated by an operator passphrase ceremony).

**Security posture:** CORS lockdown, per-IP rate limiting, input sanitization (SQL-injection and XSS rejection on journal content), global error handlers that never leak stack traces, a hash-chained audit log, signed trusted-contact links, and device-token authentication for ring data ingestion (SHA-256 token hashing + constant-time compare). Cloud AI is disabled by default and enabled only by explicit operator opt-in.

**Database:** schema covers patients, journals, moods, clinical notes, crisis state/log, bookings, follow-ups, ring devices and sensor logs, risk assessments, AI analyses, notifications, audit log, and the append-only event store.

**Testing:** 82 backend tests (auth, journal pipeline, crisis trigger + cooldown, risk engine, ring ingestion, exports, event store, model registry) plus a 14-case golden-set gate (risk bands, triggers, emotion labels) enforced in CI; frontend builds are gated on `tsc` + Vite.

## 10. Deployment, Accessibility, and Sustainability

The platform requires zero financial infrastructure:
- **Framework:** FastAPI + React (open-source)
- **AI:** Custom `sentinel` model via Ollama (fully offline, 4.4 GB, 7.2B parameters) or Groq Cloud API (free tier, opt-in)
- **Storage:** SQLite/PostgreSQL with transaction-safe operations
- **Encryption:** Fernet symmetric encryption for sensitive fields; bcrypt + PBKDF2 for passwords
- **Hardware:** Consumer smart rings (Oura/Ultrahuman class) via secured device-token ingestion; deterministic simulator for development
- **Hosting:** Render.com (free HTTPS, auto-deploy from GitHub)
- **Mobile:** PWA support — "Add to Home Screen" on any device

Total monthly operating cost: $0.

## 11. Conclusion

Sentinel demonstrates that comprehensive, dual-sided mental health technology is achievable at zero infrastructure cost. Its uniqueness lies not in any single feature but in its architecture — a tri-directional hardware-software ecosystem connecting patients, psychologists, and trusted contacts through synchronized interfaces, unified psychophysiological data streams with automated emotion classification, and closed clinical workflows. It protects patients through automated crisis response and daily mood tracking, supports clinicians through AI-driven workload reduction with dual-mode summarization (patient empathy + clinical structure), and integrates trusted contacts into the care network. Its local AI option respects the most stringent privacy requirements.

By design, it acknowledges a truth often omitted from clinical systems: the psychologist is as vulnerable to the system's demands as the patient. Sentinel protects both — or it protects neither.

---

Copyright 2026 Sentinel Ecosystem (Independent Research)

Licensed under the Apache License, Version 2.0.
