from alembic import op
import sqlalchemy as sa

revision = "f2bc51085aee"
down_revision = "e1ab40f749dd"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("products",sa.Column("archived_at",sa.DateTime(timezone=True),nullable=True))
    op.create_check_constraint("archived_product_is_inactive","products","archived_at IS NULL OR NOT is_active")


def downgrade():
    op.drop_constraint("archived_product_is_inactive","products",type_="check")
    op.drop_column("products","archived_at")
