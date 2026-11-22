"""add vpn trial system

Revision ID: 2b7d1f4c9a11
Revises: 9800d614934c
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2b7d1f4c9a11"
down_revision: Union[str, Sequence[str], None] = "9800d614934c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vpn_trial_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("panel_id", sa.Integer(), nullable=True),
        sa.Column("inbound_id", sa.Integer(), nullable=True),
        sa.Column("volume_gb", sa.Integer(), server_default="0", nullable=False),
        sa.Column("duration_hours", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["panel_id"], ["vpn_panels.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["inbound_id"], ["vpn_inbounds.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "vpn_trial_claims",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("panel_id", sa.Integer(), nullable=True),
        sa.Column("inbound_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["panel_id"], ["vpn_panels.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["inbound_id"], ["vpn_inbounds.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_user_id"),
    )
    op.create_index("ix_vpn_trial_claims_telegram_user_id", "vpn_trial_claims", ["telegram_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_vpn_trial_claims_telegram_user_id", table_name="vpn_trial_claims")
    op.drop_table("vpn_trial_claims")
    op.drop_table("vpn_trial_settings")
