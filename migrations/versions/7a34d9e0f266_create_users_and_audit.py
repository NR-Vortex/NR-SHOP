"""create users and audit logs"""
from alembic import op
import sqlalchemy as sa
revision = "7a34d9e0f266"
down_revision = "6f23c8d9e155"
branch_labels = None
depends_on = None
def upgrade():
    op.create_table("users", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("telegram_id", sa.BigInteger(), nullable=False), sa.Column("full_name", sa.String(255), server_default="", nullable=False), sa.Column("username", sa.String(255)), sa.Column("phone", sa.String(32)), sa.Column("is_blocked", sa.Boolean(), server_default="false", nullable=False), sa.Column("blocked_reason", sa.Text()), sa.Column("blocked_by", sa.BigInteger()), sa.Column("blocked_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.UniqueConstraint("telegram_id"))
    for col in ("telegram_id", "username", "phone"): op.create_index(f"ix_users_{col}", "users", [col])
    op.create_table("user_audit_logs", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.BigInteger(), nullable=False), sa.Column("admin_id", sa.BigInteger(), nullable=False), sa.Column("action", sa.String(32), nullable=False), sa.Column("details", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_user_audit_logs_user_id", "user_audit_logs", ["user_id"])
def downgrade():
    op.drop_index("ix_user_audit_logs_user_id", table_name="user_audit_logs"); op.drop_table("user_audit_logs")
    for col in ("phone", "username", "telegram_id"): op.drop_index(f"ix_users_{col}", table_name="users")
    op.drop_table("users")
