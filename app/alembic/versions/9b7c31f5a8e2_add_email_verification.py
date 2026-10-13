"""Add email verification state to users.

Revision ID: 9b7c31f5a8e2
Revises: aa1a953d92bd
Create Date: 2026-09-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9b7c31f5a8e2"
down_revision: Union[str, Sequence[str], None] = "aa1a953d92bd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_email_verified",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
    )
    op.alter_column(
        "users",
        "is_email_verified",
        server_default=sa.false(),
    )


def downgrade() -> None:
    op.drop_column("users", "is_email_verified")