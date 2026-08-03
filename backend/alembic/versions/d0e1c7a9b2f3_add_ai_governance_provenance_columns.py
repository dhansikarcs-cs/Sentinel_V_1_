"""add ai governance provenance columns

Revision ID: d0e1c7a9b2f3
Revises: 4ff25c97017e
Create Date: 2026-08-03 12:00:00.000000

"""

import contextlib
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d0e1c7a9b2f3"
down_revision: Union[str, Sequence[str], None] = "4ff25c97017e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ADD_COLUMNS = [
    ("ai_analyses", "prompt_version", sa.String()),
    ("clinical_notes", "approved_by", sa.String()),
    ("clinical_notes", "approved_at", sa.String()),
    ("followups", "approved_by", sa.String()),
    ("followups", "approved_at", sa.String()),
]


def _table_columns(table_name: str) -> set[str]:
    conn = op.get_bind()
    result = conn.execute(sa.text(f"PRAGMA table_info({table_name})"))
    return {row[1] for row in result}


def upgrade() -> None:
    with contextlib.suppress(Exception):
        for table_name, column_name, column_type in ADD_COLUMNS:
            if column_name not in _table_columns(table_name):
                op.add_column(table_name, sa.Column(column_name, column_type, server_default="", nullable=False))


def downgrade() -> None:
    with contextlib.suppress(Exception):
        for table_name, column_name, _column_type in ADD_COLUMNS:
            if column_name in _table_columns(table_name):
                op.drop_column(table_name, column_name)
