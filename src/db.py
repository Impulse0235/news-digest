import argparse
import os
import sqlite3

DB_PATH = os.environ.get("DB_PATH", "/app/data/state.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY,          -- sha256 of the link, so re-fetching is a no-op
    title TEXT NOT NULL,
    link TEXT NOT NULL,
    source TEXT NOT NULL,
    published_at TIMESTAMP,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cluster_id TEXT,               -- set by dedup.py once duplicates are grouped
    alerted INTEGER DEFAULT 0,     -- 1 once an instant alert has fired for this item
    alert_checked INTEGER DEFAULT 0,  -- 1 once alert_check.py has reviewed this item at all
    digested INTEGER DEFAULT 0    -- 1 once included in a daily digest email
);

CREATE INDEX IF NOT EXISTS idx_items_published_at ON items(published_at);
CREATE INDEX IF NOT EXISTS idx_items_cluster_id ON items(cluster_id);
CREATE INDEX IF NOT EXISTS idx_items_alerted ON items(alerted);
CREATE INDEX IF NOT EXISTS idx_items_digested ON items(digested);

CREATE TABLE IF NOT EXISTS digests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    payload_json TEXT NOT NULL,   -- {"top10": [...], "rest": [...]}
    sent INTEGER DEFAULT 0        -- 1 once email_digest.py has actually sent this
);
"""


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.execute("PRAGMA journal_mode=WAL")  # safer for a container that writes every 15 min
    return conn


def init_db():
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.commit()

    # Lightweight migration: add columns that didn't exist in earlier versions
    # of this schema, so an existing database doesn't need to be wiped.
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(items)").fetchall()}
    if "alert_checked" not in existing_cols:
        conn.execute("ALTER TABLE items ADD COLUMN alert_checked INTEGER DEFAULT 0")
        conn.commit()
        print("[db] Migrated: added items.alert_checked column")

    conn.close()
    print(f"[db] Initialized schema at {DB_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", action="store_true", help="Create the schema if it doesn't exist")
    args = parser.parse_args()
    if args.init:
        init_db()
