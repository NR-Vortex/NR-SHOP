"""create referrals"""
from alembic import op
import sqlalchemy as sa
revision = "6f23c8d9e155"
down_revision = "5e12b3c7d844"
branch_labels = None
depends_on = None
def upgrade():
    op.create_table("referrals", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("referrer_user_id", sa.BigInteger(), nullable=False), sa.Column("referred_user_id", sa.BigInteger(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.UniqueConstraint("referred_user_id", name="uq_referrals_referred_user"))
    op.create_index("ix_referrals_referrer_user_id", "referrals", ["referrer_user_id"]); op.create_index("ix_referrals_referred_user_id", "referrals", ["referred_user_id"])
def downgrade():
    op.drop_index("ix_referrals_referred_user_id", table_name="referrals"); op.drop_index("ix_referrals_referrer_user_id", table_name="referrals"); op.drop_table("referrals")
