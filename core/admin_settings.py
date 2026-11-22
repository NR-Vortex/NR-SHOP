import os
from pathlib import Path
from sqlite3 import connect
from contextlib import closing

DATA_DIR = Path(os.getenv("NR_SHOP_DATA_DIR") or Path(__file__).resolve().parents[1])
STORE = DATA_DIR / "admin_settings.sqlite3"


def read_setting(key, default=None):
    if not STORE.exists():
        return default
    with closing(connect(STORE)) as db:
        db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        row = db.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row[0] if row else default


def write_setting(key, value):
    with closing(connect(STORE)) as db, db:
        db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        db.execute("INSERT OR REPLACE INTO settings VALUES (?, ?)", (key, value))


def content_prefix(key):
    from html import escape
    value = read_setting(key, "")
    return escape(value) + "\n\n" if value else ""


def representative_db():
    db = connect(STORE)
    db.execute("CREATE TABLE IF NOT EXISTS representatives (telegram_id INTEGER PRIMARY KEY, name TEXT NOT NULL, bot TEXT NOT NULL, active INTEGER NOT NULL)")
    return db


