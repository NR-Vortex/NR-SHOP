from alembic import op

revision = "cf892de527bb"
down_revision = "be781cd416aa"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE agency_customers (
        bot_id BIGINT NOT NULL, customer BIGINT NOT NULL, display_name TEXT,
        PRIMARY KEY (bot_id, customer))""")
    op.execute("""INSERT INTO agency_customers(bot_id,customer)
        SELECT bot_id,customer FROM agency_retail_orders
        UNION SELECT bot_id,customer FROM agency_services""")


def downgrade():
    op.drop_table("agency_customers")
