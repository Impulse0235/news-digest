import json
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from openai import OpenAI

from db import get_connection

# GitHub Models — free, OpenAI-compatible, authenticated with a GitHub
# personal access token you already have an account for (no new signup).
GH_MODELS_BASE_URL = "https://models.github.ai/inference"
GH_MODELS_MODEL = os.environ.get("GH_MODELS_MODEL", "openai/gpt-4o-mini")
DIGEST_WINDOW_HOURS = int(os.environ.get("DIGEST_WINDOW_HOURS", "24"))

# "Mix of both, AI's judgment call" — the prompt explicitly tells the model
# to weigh real-world significance AND cross-outlet coverage, and to use
# its own judgment on the tradeoff rather than optimizing either alone.
SYSTEM_PROMPT = """You are a news editor building a daily digest. You will be given
a list of news story clusters from the last 24 hours, each with an id, a
representative title, and the outlets that covered it.

Pick the 10 most important stories overall. Use your own judgment, weighing
BOTH real-world significance/impact AND how widely a story was covered
(coverage by several independent outlets is a signal it matters, but a
single-source story can still be top-10 if it's genuinely significant).

Return ONLY valid JSON, no other text, no markdown fences, in this exact shape:
{
  "top10": [
    {"cluster_id": "...", "summary": "2-3 sentence plain-language summary", "category": "..."}
  ],
  "rest_order": ["cluster_id", "cluster_id", ...]
}

"category" must be exactly one of: world, security, legal, technology, business,
science, health, sports, other — pick the single best fit, use "other" if none apply.

"top10" must have exactly 10 entries (fewer only if there genuinely aren't
10 clusters available), ordered most important first. "rest_order" must
list every remaining cluster_id, most important first, no summary needed."""


def load_clusters():
    conn = get_connection()
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=DIGEST_WINDOW_HOURS)).isoformat()

    rows = conn.execute(
        """
        SELECT id, title, link, source, published_at, cluster_id
        FROM items
        WHERE digested = 0 AND published_at >= ?
        ORDER BY published_at ASC
        """,
        (cutoff,),
    ).fetchall()
    conn.close()

    clusters = defaultdict(list)
    for item_id, title, link, source, published_at, cluster_id in rows:
        key = cluster_id or item_id  # fallback if dedup hasn't run yet
        clusters[key].append(
            {"id": item_id, "title": title, "link": link, "source": source, "published_at": published_at}
        )
    return clusters


def build_cluster_input(clusters):
    lines = []
    representatives = {}
    for cluster_id, items in clusters.items():
        items_sorted = sorted(items, key=lambda i: i["published_at"])
        rep_title = items_sorted[0]["title"]
        representatives[cluster_id] = {"title": rep_title, "items": items_sorted}
        sources = ", ".join(sorted({i["source"] for i in items}))
        lines.append(f'- id: {cluster_id} | title: "{rep_title}" | sources: {sources}')
    return "\n".join(lines), representatives


def call_ai(cluster_text):
    client = OpenAI(api_key=os.environ["GH_MODELS_TOKEN"], base_url=GH_MODELS_BASE_URL)
    response = client.chat.completions.create(
        model=GH_MODELS_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": cluster_text},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content


def parse_ai_response(raw_text):
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    return json.loads(text)


def links_for(rep):
    return [{"source": i["source"], "link": i["link"]} for i in rep["items"]]


def build_digest():
    clusters = load_clusters()
    if not clusters:
        print("[summarize] No un-digested items in the window — nothing to summarize")
        return

    cluster_text, representatives = build_cluster_input(clusters)
    print(f"[summarize] Sending {len(clusters)} cluster(s) to GitHub Models ({GH_MODELS_MODEL})...")

    raw = call_ai(cluster_text)
    try:
        parsed = parse_ai_response(raw)
    except json.JSONDecodeError as e:
        print(f"[summarize] Failed to parse AI response as JSON: {e}")
        print(f"[summarize] Raw response was:\n{raw}")
        return

    top10_payload = []
    included_ids = set()
    for entry in parsed.get("top10", []):
        cid = entry.get("cluster_id")
        if cid not in representatives or cid in included_ids:
            continue
        rep = representatives[cid]
        top10_payload.append(
            {
                "title": rep["title"],
                "summary": entry.get("summary", ""),
                "category": entry.get("category", "other"),
                "links": links_for(rep),
            }
        )
        included_ids.add(cid)

    rest_payload = []
    for cid in parsed.get("rest_order", []):
        if cid in included_ids or cid not in representatives:
            continue
        rep = representatives[cid]
        rest_payload.append({"title": rep["title"], "links": links_for(rep)})
        included_ids.add(cid)

    # Anything the model forgot to place still gets included, so nothing
    # silently vanishes from the digest due to an incomplete AI response.
    for cid, rep in representatives.items():
        if cid not in included_ids:
            rest_payload.append({"title": rep["title"], "links": links_for(rep)})
            included_ids.add(cid)

    payload = {"top10": top10_payload, "rest": rest_payload}

    conn = get_connection()
    conn.execute("INSERT INTO digests (payload_json) VALUES (?)", (json.dumps(payload),))

    all_item_ids = [i["id"] for items in clusters.values() for i in items]
    conn.executemany("UPDATE items SET digested = 1 WHERE id = ?", [(i,) for i in all_item_ids])
    conn.commit()
    conn.close()

    print(
        f"[summarize] Digest built: {len(top10_payload)} top stories, "
        f"{len(rest_payload)} other(s). Marked {len(all_item_ids)} item(s) as digested."
    )


if __name__ == "__main__":
    build_digest()
