import hashlib
import os
import time
from datetime import datetime, timezone

import feedparser
import yaml

from db import get_connection

CONFIG_PATH = os.environ.get("FEEDS_CONFIG", "/app/config/feeds.yaml")


def make_id(link: str) -> str:
    return hashlib.sha256(link.encode("utf-8")).hexdigest()


def load_feeds():
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f) or {}
    return cfg.get("feeds", [])


def parse_published(entry):
    if getattr(entry, "published_parsed", None):
        return datetime.fromtimestamp(time.mktime(entry.published_parsed), tz=timezone.utc)
    return datetime.now(timezone.utc)


def fetch_all():
    feeds = load_feeds()
    if not feeds:
        print("[fetch] No feeds configured in feeds.yaml — nothing to do")
        return

    conn = get_connection()
    new_count = 0

    for feed in feeds:
        name = feed.get("name", feed.get("url"))
        url = feed["url"]
        print(f"[fetch] Pulling {name}...")

        parsed = feedparser.parse(url)
        if parsed.bozo and not parsed.entries:
            print(f"[fetch]   warning: could not parse {name} ({parsed.bozo_exception})")
            continue

        for entry in parsed.entries:
            link = entry.get("link")
            title = entry.get("title")
            if not link or not title:
                continue

            item_id = make_id(link)
            published_at = parse_published(entry)

            cur = conn.execute(
                """
                INSERT OR IGNORE INTO items (id, title, link, source, published_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (item_id, title, link, name, published_at.isoformat()),
            )
            if cur.rowcount:
                new_count += 1

    conn.commit()
    conn.close()
    print(f"[fetch] Done — {new_count} new item(s) added")


if __name__ == "__main__":
    fetch_all()
