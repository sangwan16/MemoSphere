"""Add recipients to post shares.

Revision ID: c71d90a6f42b
Revises: 4a2d8f61c930
Create Date: 2026-11-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c71d90a6f42b"
down_revision: str | Sequence[str] | None = "4a2d8f61c930"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("shares", sa.Column("recipient_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_shares_recipient_id_users",
        "shares",
        "users",
        ["recipient_id"],
        ["id"],
    )
    op.create_index(op.f("ix_shares_recipient_id"), "shares", ["recipient_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_shares_recipient_id"), table_name="shares")
    op.drop_constraint("fk_shares_recipient_id_users", "shares", type_="foreignkey")
    op.drop_column("shares", "recipient_id")
