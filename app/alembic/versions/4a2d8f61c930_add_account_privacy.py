"""Add account privacy preference.

Revision ID: 4a2d8f61c930
Revises: d614e7c2a91f
Create Date: 2026-10-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4a2d8f61c930"
down_revision: Union[str, Sequence[str], None] = "d614e7c2a91f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_public", sa.Boolean(), server_default=sa.true(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "is_public")
