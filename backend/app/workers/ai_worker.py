import asyncio
import json
import logging
from datetime import UTC, datetime

from app.events import get_event_bus
from app.ml.crisis_policy import CRISIS_POLICY
from app.ml.risk_engine import assess_risk_with_history
from app.services.ai_service import summarize_journal

logger = logging.getLogger("sentinel.workers.ai")

EMOTION_CLASSIFIER_VERSION = "1.0.0"
RISK_ENGINE_VERSION = "1.0.0"


def analyze_journal_background(journal_id: int, raw_content: str, patient_username: str) -> None:
    logger.info("Background AI analysis started for journal %s", journal_id)
    now = datetime.now(UTC).isoformat()

    patient_result = summarize_journal(raw_content, mode="patient")
    clinical_result = summarize_journal(raw_content, mode="clinical")

    from app.core.database import SessionLocal as _PreSessionDB
    from app.services.patient_context import recent_patient_context

    _pre_db = _PreSessionDB()
    try:
        _recent = recent_patient_context(_pre_db, patient_username, journal_limit=10).journals
        _recent_texts = [j.raw_content for j in reversed(_recent) if j.id != journal_id]
    except Exception:
        _recent_texts = []
    finally:
        _pre_db.close()

    risk = assess_risk_with_history(raw_content, recent_texts=_recent_texts)

    emotion_probs = risk.get("emotion_probabilities", {})
    if isinstance(emotion_probs, str):
        try:
            emotion_probs = json.loads(emotion_probs)
        except (json.JSONDecodeError, TypeError):
            emotion_probs = {}
    emotion_probs_json = (
        json.dumps(emotion_probs)
        if isinstance(emotion_probs, dict)
        else patient_result.get("emotion_probabilities", "{}")
    )

    from app.core.database import SessionLocal
    from app.models.ai_analysis import AIAnalysis
    from app.models.emotion_result import EmotionResult
    from app.models.journal import JournalEntry
    from app.models.notification import Notification
    from app.models.risk_assessment import RiskAssessment

    db = SessionLocal()
    try:
        entry = db.query(JournalEntry).filter(JournalEntry.id == journal_id).first()
        if entry:
            entry.summary = patient_result.get("summary", raw_content[:200])
            entry.clinical_summary = clinical_result.get("summary", patient_result.get("summary", raw_content[:200]))
            entry.ai_source = clinical_result.get("ai_source", "rule")
            entry.emotions = clinical_result.get("emotions", "")
            entry.emotion_probabilities = emotion_probs_json
            db.commit()

        emotion_result = EmotionResult(
            journal_id=journal_id,
            patient_username=patient_username,
            **{k: v for k, v in emotion_probs.items() if hasattr(EmotionResult, k)},
            model_version=EMOTION_CLASSIFIER_VERSION,
            created_at=now,
        )
        db.add(emotion_result)
        db.flush()

        risk_score = risk.get("risk_score", 0)
        risk_score = max(0, min(10, int(risk_score))) if isinstance(risk_score, (int, float)) else 0
        priority = CRISIS_POLICY.triage_priority(risk_score)

        ai_analysis = AIAnalysis(
            journal_id=journal_id,
            patient_username=patient_username,
            summary_patient=patient_result.get("summary", raw_content[:200]),
            summary_clinical=clinical_result.get("summary", patient_result.get("summary", raw_content[:200])),
            priority=priority,
            confidence=round(sum(emotion_probs.values()) / len(emotion_probs) if emotion_probs else 0.5, 4),
            explanation=json.dumps(risk.get("explainability", {})),
            provider=patient_result.get("ai_source", "rule"),
            model_version=EMOTION_CLASSIFIER_VERSION,
            prompt_version=clinical_result.get("prompt_version", "rule"),
            created_at=now,
        )
        db.add(ai_analysis)

        risk_assessment = RiskAssessment(
            journal_id=journal_id,
            emotion_result_id=emotion_result.id,
            sensor_reading_id=None,
            patient_username=patient_username,
            risk_score=risk_score,
            triggered=1 if risk.get("triggered", False) else 0,
            confidence=round(risk.get("confidence", 0.0), 4)
            if isinstance(risk.get("confidence"), (int, float))
            else 0.0,
            explanation=json.dumps(risk.get("explainability", {})),
            algorithm_version=RISK_ENGINE_VERSION,
            created_at=now,
        )
        db.add(risk_assessment)

        if CRISIS_POLICY.should_notify(risk_score):
            notif = Notification(
                patient_username=patient_username,
                title="Crisis Risk Detected",
                message=CRISIS_POLICY.notify_message.format(risk_score=risk_score),
                notification_type="crisis",
                read=0,
                sent_at=now,
            )
            db.add(notif)

        if CRISIS_POLICY.should_auto_trigger(risk_score, risk.get("triggered", False)):
            from app.models.crisis import CrisisLog, CrisisState

            recent_trigger = (
                db.query(CrisisLog)
                .filter(
                    CrisisLog.patient == patient_username,
                    CrisisLog.event.in_(["crisis_auto_triggered", "triggered", "resolved"]),
                )
                .order_by(CrisisLog.timestamp.desc())
                .first()
            )
            if recent_trigger:
                try:
                    last_time = datetime.fromisoformat(recent_trigger.timestamp)
                    cooldown_left = CRISIS_POLICY.trigger_cooldown_seconds - int(
                        (datetime.now(UTC) - last_time).total_seconds()
                    )
                except Exception:
                    cooldown_left = 0
                if cooldown_left > 0:
                    logger.info(
                        "Skipping auto-trigger for journal %s: patient %s in cooldown (%ss left)",
                        journal_id,
                        patient_username,
                        cooldown_left,
                    )
                    db.commit()
                    bus = get_event_bus()
                    bus.emit(
                        "journal:summarized",
                        journal_id=journal_id,
                        patient_username=patient_username,
                        summary=entry.summary if entry else "",
                        clinical_summary=entry.clinical_summary if entry else "",
                        emotions=entry.emotions if entry else "",
                        emotion_probabilities=emotion_probs_json,
                        ai_source=entry.ai_source if entry else "rule",
                        risk_score=risk_score,
                        risk_triggered=risk.get("triggered", False),
                        risk_explainability=risk.get("explainability"),
                    )
                    return

            existing = db.query(CrisisState).first()
            if not existing:
                existing = CrisisState(active=0)
                db.add(existing)
            if not existing.active:
                existing.active = 1
                existing.patient_username = patient_username
                existing.triggered_at = now
                existing.triggered_by = "ai_detection"
                existing.acknowledged = 0
                existing.trusted_contact_notified = 0
                existing.trustee_acknowledged = 0
                existing.trustee_clicked = 0
                existing.helpline_escalated = 0
                log = CrisisLog(
                    event="crisis_auto_triggered",
                    patient=patient_username,
                    timestamp=now,
                    source="ai_detection",
                    details=CRISIS_POLICY.crisis_log_details.format(risk_score=risk_score),
                )
                db.add(log)
                notif_psych = Notification(
                    patient_username=patient_username,
                    title="CRITICAL: Auto-Crisis Triggered",
                    message=CRISIS_POLICY.auto_trigger_message.format(
                        risk_score=risk_score, journal_id=journal_id, delay=CRISIS_POLICY.trusted_contact_delay_seconds
                    ),
                    notification_type="crisis",
                    read=0,
                    sent_at=now,
                )
                db.add(notif_psych)

                from app.services.websocket_manager import manager

                loop = asyncio.get_event_loop()
                loop.create_task(
                    manager.broadcast_to_psych(
                        "crisis_alert",
                        {
                            "patient": patient_username,
                            "risk_score": risk_score,
                            "message": CRISIS_POLICY.auto_trigger_alert.format(
                                patient=patient_username, risk_score=risk_score
                            ),
                            "timestamp": datetime.now(UTC).isoformat(),
                        },
                    )
                )
        elif CRISIS_POLICY.should_warn(risk_score):
            from app.services.websocket_manager import manager

            loop = asyncio.get_event_loop()
            loop.create_task(
                manager.broadcast_to_psych(
                    "risk_warning",
                    {
                        "patient": patient_username,
                        "risk_score": risk_score,
                        "message": CRISIS_POLICY.risk_warning_alert.format(
                            patient=patient_username, risk_score=risk_score
                        ),
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )
            )

        db.commit()
        logger.info(
            "AI analysis complete for journal %s (emotion_result=%d, risk=%d)",
            journal_id,
            emotion_result.id,
            risk_score,
        )

        bus = get_event_bus()
        bus.emit(
            "journal:summarized",
            journal_id=journal_id,
            patient_username=patient_username,
            summary=entry.summary if entry else "",
            clinical_summary=entry.clinical_summary if entry else "",
            emotions=entry.emotions if entry else "",
            emotion_probabilities=emotion_probs_json,
            ai_source=entry.ai_source if entry else "rule",
            risk_score=risk_score,
            risk_triggered=risk.get("triggered", False),
            risk_explainability=risk.get("explainability"),
        )
    except Exception as e:
        logger.exception("Background AI analysis failed for journal %s: %s", journal_id, e)
    finally:
        db.close()
