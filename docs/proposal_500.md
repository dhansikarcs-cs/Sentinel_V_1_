# The Sentinel System: An Assistant for the Overloaded Clinician

## 1. The Problem — Buried, Not Absent

Mental health clinicians are not failing their patients; they are drowning. Patients spend 167 of every 168 hours out of sight — risk builds in those unseen hours and surfaces only at the next appointment. The clinician has no time to look: documentation, journal review, and manual risk assessment consume hours each week, and India runs 0.75 psychiatrists per 100,000 against a WHO recommendation of 1 per 10,000. Telehealth is appointment-only; wellness apps are generic. Between-session hours stay invisible, so risk is discovered late and crises land without warning.

## 2. Two Signals, One Picture

Sentinel compares what a patient says with what their body reports, and flags when they disagree.

**The subjective channel — words.** Every journal entry is read, summarized, and classified across 28 emotion labels by a classifier trained on 48,836 real GoEmotions examples (official test micro-F1 0.464, leak-free). Keywords are negation-aware, so "I'm not okay" is never read as positive.

**The objective channel — the body.** A companion ring streams biomarkers over a securely paired (token-fingerprinted) connection: heart rate, heart-rate variability (HRV, with RMSSD/SDNN), stress level, sleep hours, and blood-oxygen saturation.

**The discrepancy engine.** When the channels disagree, Sentinel notices. A journal that reads positive while HRV is low and resting heart rate is high is a red flag — the patient may be masking, and the risk assessment must include that tension, not just the words. This comparison runs in ~0.1 ms and broadcasts an alert the moment a mismatch is detected, so the clinician sees the contradiction at a glance instead of discovering it weeks later in a chart.

## 3. AI and Hardware Working Together

The stacked signals feed the risk engine, which reports a numeric score with a plain-language explanation of which signals contributed — never a black box. When a crisis triggers, a staged protocol acts automatically: an immediate siren with an explainable reason, a trusted-contact email with a signed, expiring link at 30 seconds, and helpline escalation at 60 seconds. The clinician halts it with one tap and the timer freezes; they are never the single point of failure. Self-monitoring metrics also surface the clinician's own stress and fatigue, guarding against secondary trauma in the person holding every patient's story.

## 4. Judgment Stays Human

The AI summarizes, triages, and alerts — it never diagnoses or prescribes. Every output carries its model and confidence, and nothing enters a clinical record without clinician approval. The AI runs locally, so patient data never leaves the clinic.

## 5. Validation and Cost

Sentinel passes 99/99 automated tests, detects discrepancies with 96% accuracy in ~0.1 ms, and ships a 47-run timing benchmark — all reproducible. It runs on free infrastructure at a $0 monthly cost, deployable in any clinic, school, or community center.

## 6. The Promise

Sentinel does not replace clinical judgment. It gives it back the time it lost — hours each week, a safety net that never sleeps, and the ability to see the patient whose words and body disagree before the words turn into a crisis.
