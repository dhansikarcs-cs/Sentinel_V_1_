"""Single source of truth for assembling a patient's recent clinical context.

Constitution principles #5 and #6: context is built once, here, and every
handler consumes this one build. Do not add new direct journal/mood/ring/
followup queries elsewhere for single-patient context reads.

Panel-level analytics (e.g. compliance-radar iterating a whole psychologist
panel) are aggregate queries and are a legitimate direct-DB exception.
"""

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.followup import FollowupTask
from app.models.journal import JournalEntry
from app.models.mood import MoodLog
from app.models.ring import RingSensorLog


@dataclass
class PatientContext:
    username: str
    journals: list[JournalEntry] = field(default_factory=list)
    moods: list[MoodLog] = field(default_factory=list)
    ring_logs: list[RingSensorLog] = field(default_factory=list)
    followups: list[FollowupTask] = field(default_factory=list)

    @property
    def latest_ring(self) -> RingSensorLog | None:
        return self.ring_logs[0] if self.ring_logs else None

    @property
    def recent_mood_label(self) -> str:
        return self.moods[0].label if self.moods else "unknown"

    @property
    def latest_bpm(self) -> int:
        return self.latest_ring.bpm if self.latest_ring and self.latest_ring.bpm else 72

    @property
    def latest_stress(self) -> int:
        return self.latest_ring.stress if self.latest_ring and self.latest_ring.stress else 35

    def recent_text(self, excerpt_len: int = 500) -> str:
        if not self.journals:
            return "No recent journal entries"
        return self.journals[0].raw_content[:excerpt_len]


def recent_patient_context(
    db: Session,
    username: str,
    *,
    journal_limit: int = 5,
    mood_limit: int = 7,
    ring_limit: int = 1,
    include_followups: bool = False,
) -> PatientContext:
    ctx = PatientContext(username=username)

    ctx.journals = (
        db.query(JournalEntry)
        .filter(JournalEntry.patient_username == username)
        .order_by(JournalEntry.timestamp.desc())
        .limit(journal_limit)
        .all()
    )
    ctx.moods = (
        db.query(MoodLog)
        .filter(MoodLog.patient_username == username)
        .order_by(MoodLog.timestamp.desc())
        .limit(mood_limit)
        .all()
    )
    ctx.ring_logs = (
        db.query(RingSensorLog)
        .filter(RingSensorLog.patient_username == username)
        .order_by(RingSensorLog.logged_at.desc())
        .limit(ring_limit)
        .all()
    )
    if include_followups:
        ctx.followups = (
            db.query(FollowupTask)
            .filter(FollowupTask.patient_username == username)
            .order_by(FollowupTask.assigned_at.desc())
            .all()
        )
    return ctx


TRIAGE_PROMPT_V1 = (
    'Triage urgency assessment for patient "{username}".\n\n'
    'Recent journal excerpt: "{recent_text}"\n'
    "Recent mood label: {recent_mood}\n"
    "Heart rate: {bpm} BPM\n"
    "Stress: {stress}\n\n"
    "Assess the urgency of this patient's situation on a scale of 1-10 (1=stable, 10=immediate crisis).\n"
    'Return ONLY valid JSON with keys: score (int), priority ("low"/"medium"/"high"), '
    "reasons (list of str), suggestion (str)."
)


def build_triage_prompt(ctx: PatientContext) -> str:
    return TRIAGE_PROMPT_V1.format(
        username=ctx.username,
        recent_text=ctx.recent_text(500),
        recent_mood=ctx.recent_mood_label,
        bpm=ctx.latest_bpm,
        stress=ctx.latest_stress,
    )


_TIER_BY_PRIORITY = {"high": "high", "medium": "attention", "low": "stable"}
_TIER_SCORE = {"crisis": 100, "high": 50, "attention": 25, "stable": 0}


def derive_triage_tier(priority: str, crisis: bool = False) -> str:
    if crisis:
        return "crisis"
    return _TIER_BY_PRIORITY.get((priority or "low").lower(), "stable")


def triage_priority_score(tier: str) -> int:
    return _TIER_SCORE.get(tier, 0)
