from alembic import op
import sqlalchemy as sa

revision = "8b45eaf10377"
down_revision = "7a34d9e0f266"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("orders", sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_orders_paid_at", "orders", ["paid_at"])


def downgrade():
    op.drop_index("ix_orders_paid_at", table_name="orders")
    op.drop_column("orders", "paid_at")
