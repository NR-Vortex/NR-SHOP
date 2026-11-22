from alembic import op
import sqlalchemy as sa

revision = "e1ab40f749dd"
down_revision = "d09a3ef638cc"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "pending_referrals",
        sa.Column("referred_user_id",sa.BigInteger(),primary_key=True),
        sa.Column("referrer_user_id",sa.BigInteger(),nullable=False),
        sa.CheckConstraint("referrer_user_id <> referred_user_id",name="pending_referral_not_self"),
    )


def downgrade():
    op.drop_table("pending_referrals")
