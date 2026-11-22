from alembic import op

revision = "ad671bc30599"
down_revision = "9c56fb021488"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE agency_services (
        reference VARCHAR(100) PRIMARY KEY, bot_id BIGINT NOT NULL,
        customer BIGINT NOT NULL, gb BIGINT NOT NULL CHECK(gb>0),
        inbound_id INTEGER NOT NULL REFERENCES vpn_inbounds(id),
        client_id VARCHAR(36) NOT NULL, subscription VARCHAR(32) NOT NULL,
        delivered BOOLEAN NOT NULL DEFAULT false)""")


def downgrade():
    op.drop_table("agency_services")
