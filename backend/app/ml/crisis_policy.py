from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TriagePriority = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class CrisisPolicy:
    """Data-driven crisis thresholds and actions, isolated from business logic.

    Every magic number that decides *what the system does* with a risk score
    lives here so the policy can be reviewed, tuned and tested in one place.
    """

    auto_trigger_threshold: int = 8
    notify_threshold: int = 7
    warn_threshold: int = 6
    elevated_alert_threshold: int = 7
    low_priority_max: int = 3
    medium_priority_max: int = 6
    trusted_contact_delay_seconds: int = 30
    helpline_escalation_delay_seconds: int = 60
    trigger_cooldown_seconds: int = 3600

    notify_message: str = (
        "Your recent journal entry flagged a risk score of {risk_score}/10. Your psychologist has been notified."
    )
    auto_trigger_message: str = (
        "CRITICAL: AI detected crisis-level risk (score {risk_score}/10) in journal #{journal_id}. "
        "Crisis protocol activated. Trusted contact will be notified in {delay}s."
    )
    crisis_log_details: str = "Risk score {risk_score}/10, triggered by AI emotion+keyword analysis"
    auto_trigger_alert: str = "Auto-detected crisis for {patient} (risk: {risk_score}/10)"
    risk_warning_alert: str = "High risk detected for {patient} (risk: {risk_score}/10)"

    def triage_priority(self, risk_score: int | float) -> TriagePriority:
        if risk_score <= self.low_priority_max:
            return "low"
        if risk_score <= self.medium_priority_max:
            return "medium"
        return "high"

    def should_auto_trigger(self, risk_score: int | float, triggered: bool) -> bool:
        return bool(triggered) and risk_score >= self.auto_trigger_threshold

    def should_notify(self, risk_score: int | float) -> bool:
        return risk_score >= self.notify_threshold

    def should_warn(self, risk_score: int | float) -> bool:
        return risk_score >= self.warn_threshold

    def should_elevate_alert(self, risk_score: int | float) -> bool:
        return risk_score >= self.elevated_alert_threshold

    def action_messages(self) -> dict[str, str]:
        return {
            "notify": self.notify_message,
            "auto_trigger": self.auto_trigger_message,
            "crisis_log_details": self.crisis_log_details,
            "auto_trigger_alert": self.auto_trigger_alert,
            "risk_warning_alert": self.risk_warning_alert,
        }


CRISIS_POLICY: CrisisPolicy = CrisisPolicy()
