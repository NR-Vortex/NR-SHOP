"""Purchased wholesale traffic, credited in the wallet debit transaction."""
from alembic import op
import sqlalchemy as sa

revision = "9c56fb021488"
down_revision = "8b45eaf10377"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("agency_volume",
        sa.Column("bot_id", sa.BigInteger(), primary_key=True),
        sa.Column("owner_id", sa.BigInteger(), nullable=False),
        sa.Column("balance_gb", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("balance_gb >= 0", name="agency_volume_nonnegative"))


def downgrade():
    op.drop_table("agency_volume")
