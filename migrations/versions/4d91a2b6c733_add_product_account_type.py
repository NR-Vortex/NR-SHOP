"""add product account type"""
from alembic import op
import sqlalchemy as sa

revision = "4d91a2b6c733"
down_revision = "3c8e2f1a7b44"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("products", sa.Column("account_type", sa.String(16), server_default="shared", nullable=False))


def downgrade():
    op.drop_column("products", "account_type")
