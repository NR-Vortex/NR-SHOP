from alembic import op

revision = "be781cd416aa"
down_revision = "ad671bc30599"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE agency_services ADD COLUMN expiry_ms BIGINT NOT NULL DEFAULT 0")
    op.execute("""CREATE TABLE agency_plans (
       id BIGSERIAL PRIMARY KEY, bot_id BIGINT NOT NULL, name TEXT NOT NULL,
       gb INTEGER NOT NULL CHECK(gb>0), days INTEGER NOT NULL CHECK(days>0),
       price BIGINT NOT NULL CHECK(price>0), active BOOLEAN NOT NULL DEFAULT TRUE)""")
    op.execute("""CREATE TABLE agency_retail_orders (
       id BIGSERIAL PRIMARY KEY, bot_id BIGINT NOT NULL, customer BIGINT NOT NULL,
       plan_id BIGINT NOT NULL REFERENCES agency_plans(id), name TEXT NOT NULL,
       gb INTEGER NOT NULL, days INTEGER NOT NULL, price BIGINT NOT NULL,
       checkout_key TEXT UNIQUE NOT NULL, payment_destination TEXT NOT NULL, receipt TEXT, status TEXT NOT NULL DEFAULT 'open',
       created_at TIMESTAMPTZ DEFAULT now())""")
    op.execute("CREATE INDEX ix_agency_retail_lookup ON agency_retail_orders(bot_id,customer,id)")


def downgrade():
    op.drop_table("agency_retail_orders")
    op.drop_table("agency_plans")
    op.drop_column("agency_services","expiry_ms")
