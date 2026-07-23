import os
import re
import uuid
from datetime import datetime, timedelta, timezone

from rapidfuzz import fuzz

from db import get_connection

# "Balanced" setting: merges stories that are clearly the same event worded
# differently across outlets, without being so loose it merges same-topic
# but genuinely distinct stories. Tune via env vars if it's too eager/shy.
WINDOW_HOURS = int(os.environ.get("DEDUP_WINDOW_HOURS", "26"))
SIMILARITY_THRESHOLD = int(os.environ.get("DEDUP_SIMILARITY_THRESHOLD", "78"))
MAX_TIME_DELTA_HOURS = int(os.environ.get("DEDUP_MAX_TIME_DELTA_HOURS", "18"))


def normalize_title(title: str) -> str:
    title = title.lower()
    title = re.sub(r"[^\w\s]", "", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title


class UnionFind:
    """Groups items transitively: if A matches B and B matches C, all three
    end up in one cluster even if A and C weren't similar enough on their own."""

    def __init__(self, ids):
        self.parent = {i: i for i in ids}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def cluster_recent_items():
    conn = get_connection()
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=WINDOW_HOURS)).isoformat()

    rows = conn.execute(
        "SELECT id, title, published_at, cluster_id FROM items WHERE published_at >= ?",
        (cutoff,),
    ).fetchall()

    if not rows:
        print("[dedup] No recent items to cluster")
        conn.close()
        return

    items = []
    for item_id, title, published_at, cluster_id in rows:
        items.append(
            {
                "id": item_id,
                "title": title,
                "norm_title": normalize_title(title),
                "published_at": datetime.fromisoformat(published_at),
                "cluster_id": cluster_id,
            }
        )

    uf = UnionFind([i["id"] for i in items])

    # Pairwise compare — fine for the volumes a personal feed list produces
    # in a day (low hundreds of items). Revisit if you subscribe to
    # hundreds of feeds and this starts taking noticeably long.
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i], items[j]

            time_delta_hours = abs((a["published_at"] - b["published_at"]).total_seconds()) / 3600
            if time_delta_hours > MAX_TIME_DELTA_HOURS:
                continue

            score = fuzz.token_sort_ratio(a["norm_title"], b["norm_title"])
            if score >= SIMILARITY_THRESHOLD:
                uf.union(a["id"], b["id"])

    groups = {}
    for item in items:
        root = uf.find(item["id"])
        groups.setdefault(root, []).append(item)

    updated = 0
    new_clusters = 0

    for group in groups.values():
        # If any item in this group already carries a cluster_id from a
        # previous run, reuse it — keeps the same story's identity stable
        # across runs instead of forking a new cluster_id every time.
        existing_ids = sorted(i["cluster_id"] for i in group if i["cluster_id"])
        cluster_id = existing_ids[0] if existing_ids else str(uuid.uuid4())
        if not existing_ids:
            new_clusters += 1

        for item in group:
            if item["cluster_id"] != cluster_id:
                conn.execute("UPDATE items SET cluster_id = ? WHERE id = ?", (cluster_id, item["id"]))
                updated += 1

    conn.commit()
    conn.close()
    print(
        f"[dedup] {len(items)} item(s) -> {len(groups)} cluster(s) "
        f"({new_clusters} new, {updated} item row(s) updated)"
    )


if __name__ == "__main__":
    cluster_recent_items()
