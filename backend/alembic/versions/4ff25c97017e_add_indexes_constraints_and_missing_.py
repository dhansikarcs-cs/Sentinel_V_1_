"""add indexes constraints and missing models

Revision ID: 4ff25c97017e
Revises: a059d07dd9b6
Create Date: 2026-07-22 20:00:57.844080

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4ff25c97017e'
down_revision: Union[str, Sequence[str], None] = 'a059d07dd9b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INDEXES = [
    ("ix_ai_created_at", "ai_analyses", ["created_at"]),
    ("ix_ai_journal_id", "ai_analyses", ["journal_id"]),
    ("ix_ai_patient_username", "ai_analyses", ["patient_username"]),
    ("ix_ai_priority", "ai_analyses", ["priority"]),
    ("ix_booking_date", "bookings", ["date"]),
    ("ix_booking_patient_username", "bookings", ["patient_username"]),
    ("ix_booking_psychologist_username", "bookings", ["psychologist_username"]),
    ("ix_booking_status", "bookings", ["status"]),
    ("ix_emo_created_at", "emotion_results", ["created_at"]),
    ("ix_emo_journal_id", "emotion_results", ["journal_id"]),
    ("ix_emo_patient_username", "emotion_results", ["patient_username"]),
    ("ix_journal_ai_source", "journal_entries", ["ai_source"]),
    ("ix_journal_patient_username", "journal_entries", ["patient_username"]),
    ("ix_journal_timestamp", "journal_entries", ["timestamp"]),
    ("ix_mood_date", "mood_log", ["date"]),
    ("ix_mood_patient_username", "mood_log", ["patient_username"]),
    ("ix_notif_patient_username", "notifications", ["patient_username"]),
    ("ix_notif_read", "notifications", ["read"]),
    ("ix_notif_sent_at", "notifications", ["sent_at"]),
    ("ix_notif_type", "notifications", ["notification_type"]),
    ("ix_ring_device_id", "ring_sensor_log", ["device_id"]),
    ("ix_ring_logged_at", "ring_sensor_log", ["logged_at"]),
    ("ix_ring_patient_username", "ring_sensor_log", ["patient_username"]),
    ("ix_risk_created_at", "risk_assessments", ["created_at"]),
    ("ix_risk_journal_id", "risk_assessments", ["journal_id"]),
    ("ix_risk_patient_username", "risk_assessments", ["patient_username"]),
    ("ix_risk_score", "risk_assessments", ["risk_score"]),
]


def _safe_create_index(conn, index_name, table_name, columns):
    try:
        op.create_index(index_name, table_name, columns, unique=False)
    except Exception:
        pass


def upgrade() -> None:
    # Add version column to journal_entries if missing
    conn = op.get_bind()
    result = conn.execute(sa.text("PRAGMA table_info(journal_entries)"))
    cols = [row[1] for row in result]
    if "version" not in cols:
        op.add_column("journal_entries", sa.Column("version", sa.Integer(), server_default="1", nullable=False))

    for index_name, table_name, columns in INDEXES:
        _safe_create_index(conn, index_name, table_name, columns)


def downgrade() -> None:
    for index_name, table_name, _columns in INDEXES:
        try:
            op.drop_index(index_name, table_name=table_name)
        except Exception:
            pass

    conn = op.get_bind()
    result = conn.execute(sa.text("PRAGMA table_info(journal_entries)"))
    cols = [row[1] for row in result]
    if "version" in cols:
        op.drop_column("journal_entries", "version")
