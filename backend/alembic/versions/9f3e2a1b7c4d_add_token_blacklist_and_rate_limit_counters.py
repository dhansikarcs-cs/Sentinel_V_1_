"""add token_blacklist and rate_limit_counters

Multi-worker safety: the revoked-JWT blacklist and the fixed-window rate-limit
counters move into the database so every worker shares the same state.

Revision ID: 9f3e2a1b7c4d
Revises: d0e1c7a9b2f3
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "9f3e2a1b7c4d"
down_revision: str | Sequence[str] | None = "d0e1c7a9b2f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    from sqlalchemy import inspect

    inspector = inspect(op.get_bind())
    if "token_blacklist" not in inspector.get_table_names():
        op.create_table(
            "token_blacklist",
            sa.Column("jti", sa.String(), nullable=False),
            sa.Column("expires_at", sa.Float(), nullable=False),
            sa.PrimaryKeyConstraint("jti"),
        )
    if "rate_limit_counters" not in inspector.get_table_names():
        op.create_table(
            "rate_limit_counters",
            sa.Column("bucket_key", sa.String(), nullable=False),
            sa.Column("window_start", sa.Integer(), nullable=False),
            sa.Column("count", sa.Integer(), nullable=False),
            sa.PrimaryKeyConstraint("bucket_key", "window_start"),
        )


def downgrade() -> None:
    from sqlalchemy import inspect

    tables = inspect(op.get_bind()).get_table_names()
    if "rate_limit_counters" in tables:
        op.drop_table("rate_limit_counters")
    if "token_blacklist" in tables:
        op.drop_table("token_blacklist")
