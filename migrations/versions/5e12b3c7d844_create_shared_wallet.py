"""create shared wallet"""
from alembic import op
import sqlalchemy as sa

revision = "5e12b3c7d844"
down_revision = "4d91a2b6c733"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("wallets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("balance", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("balance >= 0", name="wallet_balance_non_negative"),
        sa.UniqueConstraint("telegram_user_id"))
    op.create_index("ix_wallets_telegram_user_id", "wallets", ["telegram_user_id"])
    op.create_table("wallet_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("wallet_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("balance_after", sa.BigInteger(), nullable=False),
        sa.Column("reference", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["wallet_id"], ["wallets.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("reference", name="uq_wallet_transaction_reference"))
    op.create_index("ix_wallet_transactions_wallet_id", "wallet_transactions", ["wallet_id"])


def downgrade():
    op.drop_index("ix_wallet_transactions_wallet_id", table_name="wallet_transactions")
    op.drop_table("wallet_transactions")
    op.drop_index("ix_wallets_telegram_user_id", table_name="wallets")
    op.drop_table("wallets")
