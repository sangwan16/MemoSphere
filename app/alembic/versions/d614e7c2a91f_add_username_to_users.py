"""Add username to users.

Revision ID: d614e7c2a91f
Revises: 9b7c31f5a8e2
Create Date: 2026-10-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d614e7c2a91f"
down_revision: Union[str, Sequence[str], None] = "9b7c31f5a8e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(length=30), nullable=True))
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_column("users", "username")