"""add ai account delivery tables"""
from alembic import op
import sqlalchemy as sa

revision = "3c8e2f1a7b44"
down_revision = "2b7d1f4c9a11"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ai_account_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("account_type", sa.String(16), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("encrypted_password", sa.Text(), nullable=True),
        sa.Column("custom_info", sa.Text(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("order_id"),
    )
    op.create_table(
        "ai_code_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(16), server_default="pending", nullable=False),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("order_id", "status", name="uq_ai_code_request_order_status"),
    )
    op.create_index("ix_ai_code_requests_order_id", "ai_code_requests", ["order_id"])
    op.create_index("ix_ai_code_requests_telegram_user_id", "ai_code_requests", ["telegram_user_id"])


def downgrade():
    op.drop_index("ix_ai_code_requests_telegram_user_id", table_name="ai_code_requests")
    op.drop_index("ix_ai_code_requests_order_id", table_name="ai_code_requests")
    op.drop_table("ai_code_requests")
    op.drop_table("ai_account_deliveries")
