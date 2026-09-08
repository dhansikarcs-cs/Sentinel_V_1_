# Sentinel — Pitch Deck

## Slide 01 — Sentinel

**SENTINEL**
*Privacy-first clinical intelligence for continuous mental-health support.*

Dhanshika R. — Founder
dhansika.r.cs@gmail.com | github.com/dhansikarcs-cs | linkedin.com/in/dhansika-r-cs

Early-stage / Pre-commercialisation

---

## Slide 02 — The Problem: Clinical Visibility Gaps Between Consultations

**Mental-health information is fragmented across appointments, journals, and self-reported data.**

- Clinicians obtain limited longitudinal visibility between consultations.
- Important changes in emotional state or physiological stress can be difficult to identify from isolated observations.
- Existing tools address one channel (mood trackers = subjective self-report; wearables = body data) but neither cross-validates the other.
- Continuous monitoring raises privacy and trust concerns that current architectures do not adequately address.

> **The problem is not simply collecting more data. It is turning longitudinal patient signals into useful clinical context without making patients feel constantly monitored.**

---

## Slide 03 — The Insight: Clinician-Centred, Local-First, Explainable

**The industry default: collect everything → send to cloud → generate a score.**

**Sentinel's position:**

Patient signals → local processing → contextual analysis → explainable outputs → clinician review → human decision

| Principle | What it means |
|---|---|
| **Clinician-centred** | Supports decision-making; does not autonomously diagnose or treat. |
| **Local-first** | Sensitive processing designed to occur locally where possible. |
| **Explainable** | Every risk signal traceable to specific inputs. No black-box scoring. |
| **Multi-modal** | Reads both subjective (journal text) and objective (physiology) channels. |
| **Human-in-the-loop** | Alerts escalate to a human. The system flags; people decide. |

---

## Slide 04 — The Solution: What Sentinel Actually Does

**Patient Interface**
↓
Journal entry + optional physiological signals
↓
**Sentinel Processing**
→ Emotion/context analysis (28 dimensions, real human training data)
→ Physiological signal processing (HR, HRV, stress, sleep, SpO2)
→ Cross-modal comparison (words vs body)
↓
**Explainable Contextual Signals**
→ Risk/context outputs with provenance
→ Tiered alert recommendations (5 levels)
↓
**Clinician Dashboard**
→ Patient roster + risk overview
→ Emotion timelines + discrepancy history
→ Case notes + audit trail
↓
**Human review and decision**

Three interfaces:
- **Patient portal** — journaling, emotion history, bio-trends
- **Clinician dashboard** — patient overview, risk signals, discrepancy history
- **Alert system** — tiered notifications with escalation rules and cooldown

> **Sentinel supports clinical decision-making; it does not autonomously diagnose or treat patients.**

---

## Slide 05 — Technical Architecture

**Patient Interface**
React + TypeScript, journaling, optional ring data input

**Data Collection Layer**
Structured journaling, emotion/context extraction, physiological signal ingestion

**Local Processing Layer**
NLP / emotion analysis (TF-IDF + Logistic Regression, 28 labels)
Signal processing (HeartPy-based ring integration)
Cross-signal comparison engine

**Clinical Intelligence Layer**
Weighted risk scoring (5 tiers, deterministic, auditable)
Explainable outputs with provenance
Rule-based discrepancy detection
Version-controlled model (leak-audited)

**Clinician Dashboard**
FastAPI + WebSocket (real-time)
Risk-level overview, per-patient timelines, discrepancy history, case notes

**Infrastructure**
Docker | SQLite/local storage | WebSocket | Render (cloud transport)

---

## Slide 06 — Evidence: What Has Been Built and Tested

| Evidence | Current result |
|---|---|
| Automated integration tests | 99/99 passed |
| Held-out rule-consistency evaluation | 100% under defined test setup |
| Simulated discrepancy-detection benchmark | 96% rule-consistency |
| Local inference latency | ~0.1 ms per entry (current test environment) |
| Model size | ~2.5 MB |
| Training data | 48,836 real human-labeled examples (GoEmotions, Google Research) |
| In-domain classifier performance | Micro-F1 0.464 (leak-audited, official held-out test) |
| Research manuscript | ~8,271 words, reproducibility artifacts committed |
| Statistical validation | Bootstrap 95% CIs, McNemar tests, per-class analysis |

> **Engineering and simulated evaluations; not evidence of clinical efficacy.**

---

## Slide 07 — Validation: What Has Been Proven and What Remains

**Sentinel is at the Build → Test boundary. The next evidence must come from real-world validation.**

**Technical** (underway / completed)
- Reliability and reproducibility (99/99 tests, committed artifacts)
- Local processing validation
- Benchmark performance (rule-consistency, classifier F1)
- Distribution-shift and calibration analysis (published research)

**Clinical workflow** (next)
- Clinician usability
- Workflow friction
- Alert relevance and timing
- Decision-support usefulness
- Patient onboarding and engagement
- Appropriate escalation behaviour

**Business** (next)
- Clinic willingness to pay
- Pricing validation
- Patient retention and engagement
- BYOD adoption
- Hardware economics
- Deployment complexity and scalability

> **Build → Test → Pilot → Measure → Iterate**

---

## Slide 08 — Business Model

**B2B + B2B2C**

**Clinic (B2B)**

| Product | India | U.S. |
|---|---|---|
| Clinician SaaS | ₹2,499/mo | $149/mo |
| System Maintenance | ₹999/mo | $49/mo |

**Patient (B2B2C)**

| Product | India | U.S. |
|---|---|---|
| Website Access | ₹499/mo | $29/mo |
| BYOD | ₹999/mo | $39/mo |
| Ring / HaaS | ₹1,499/mo | $79/mo |

**Infrastructure (one-time)**

| Product | India | U.S. |
|---|---|---|
| Clinic Digital Launch | ₹9,999–19,999 | $399–799 |
| Personalised Patient Website | ₹9,999–14,999 | $399–599 |

> **Pricing is a working commercial hypothesis and will be validated through pilot deployments.**

---

## Slide 09 — Market, Competitive Landscape, and Go-to-Market

**Market context**

The global mental health apps market is projected to reach USD 22.73B by 2030 (CAGR 18.0%).
*Source: MarketsandMarkets, June 2026.*

India's mental health apps market is projected to reach USD 1.41B by 2030 (CAGR 18.5%).
*Source: Grand View Research, 2024.*

India has ~200M people with a diagnosable mental health condition. Over 83% receive no treatment.
*Source: WHO, 2023; National Mental Health Survey 2015–16.*

India has ~0.75 psychiatrists per 100,000 people. WHO recommends at least 3.
*Source: Ministry of Health and Family Welfare, Rajya Sabha, July 2025; WHO Mental Health Atlas.*

> **The workforce shortage makes clinician-facing tools that extend capacity between consultations strategically important.**

**Competitive landscape**

| Category | Examples | What they do | What they do not do |
|---|---|---|---|
| Therapy platforms | BetterHelp, Talkspace | Video/text therapy with licensed therapists | No longitudinal monitoring, no biosignal analysis, no cross-modal comparison |
| AI wellness apps | Headspace, Calm, Woebot (shut down June 2025) | Self-guided CBT, meditation, mood tracking | No clinician dashboard, no physiological signals, no clinical decision support |
| Enterprise mental-health | Lyra Health, Spring Health | Employer-sponsored therapy matching and outcomes prediction | No patient-generated longitudinal data, no wearable integration, no cross-modal analysis |
| Documentation AI | Eleos Health | Ambient session note generation for therapists | No patient-facing monitoring, no biosignal processing, no risk scoring |
| Wearables | Oura Ring, Samsung Galaxy Ring | HRV, sleep, stress tracking for individual consumers | No clinical dashboard, no emotion analysis, no cross-modal comparison, no clinician workflow |

> **No existing product combines text-based emotion analysis, wearable biosignal processing, cross-modal comparison, and a clinician-centred decision-support dashboard in a single local-first architecture.**

**Go-to-market**

Phase 1 — Individual clinicians / small practices (1–3 clinicians, 20–50 patients)
→ Prove workflow fit, alert relevance, clinician adoption

Phase 2 — Multi-clinician clinics (5–10 clinicians, 100–300 patients)
→ Prove scalable deployment, validate recurring revenue and retention

Phase 3 — Larger mental-health organisations (20+ clinicians, 500+ patients)
→ Prove enterprise readiness, expand hardware and integration options

> **Model: B2B (clinic) + B2B2C (patient)**

---

## Slide 10 — Roadmap and The Ask

**Current**
MVP operational → technical validation complete → expert feedback gathering

**Next (6–12 months)**
Clinical workflow pilot → business validation → hardware/OEM validation → BYOD mobile app → product refinement

**Later (12–24 months)**
Scaled deployments (20+ clinics) → broader integrations → commercialisation → regulatory groundwork

---

**The Ask**

> **Seeking mentorship and domain expertise to stress-test Sentinel's clinical workflow, commercialisation strategy, pricing, and deployment model.**

Specifically:
- Clinical mentors (psychiatry / clinical psychology)
- Healthcare commercialisation mentors
- Pilot clinics for workflow validation
- Hardware/OEM partners for ring integration

> **The next validation stage is a clinical workflow pilot with real clinicians and patients. Sentinel is ready for it.**

---

**Dhanshika R. — Founder**
dhansika.r.cs@gmail.com | github.com/dhansikarcs-cs | linkedin.com/in/dhansika-r-cs
