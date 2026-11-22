from alembic import op
import sqlalchemy as sa

revision = "d09a3ef638cc"
down_revision = "cf892de527bb"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("products",sa.Column("vpn_volume_gb",sa.Integer(),nullable=True))
    for name,kind in (
        ("client_id",sa.String(36)),("subscription_id",sa.String(32)),
        ("subscription_url",sa.String(2048)),("expires_at",sa.DateTime(timezone=True)),("volume_gb",sa.Integer()),
    ):
        op.add_column("vpn_trial_claims",sa.Column(name,kind,nullable=True))
    op.add_column("vpn_order_details",sa.Column("subscription_id",sa.String(32),nullable=True))
    op.add_column("vpn_order_details",sa.Column("expires_at",sa.DateTime(timezone=True),nullable=True))


def downgrade():
    for name in ("expires_at","subscription_id"):
        op.drop_column("vpn_order_details",name)
    for name in ("volume_gb","expires_at","subscription_url","subscription_id","client_id"):
        op.drop_column("vpn_trial_claims",name)
    op.drop_column("products","vpn_volume_gb")
