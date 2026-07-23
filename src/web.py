from flask import Flask
import json

from db import get_connection

app = Flask(__name__)


@app.route("/")
def dashboard():
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    last_fetch = conn.execute(
        "SELECT MAX(fetched_at) FROM items"
    ).fetchone()[0]
    digest_count = conn.execute("SELECT COUNT(*) FROM digests").fetchone()[0]
    conn.close()

    return f"""
    <h1>News Digest</h1>
    <p>Items tracked: {total}</p>
    <p>Last fetch: {last_fetch or 'never'}</p>
    <p>Digests built: {digest_count} — <a href="/digest">view latest</a></p>
    <p><em>Full dashboard (feeds/keywords editor, digest archive, run-now buttons)
    is a later build step — this confirms the pipeline and database are alive.</em></p>
    """


@app.route("/digest")
def latest_digest():
    conn = get_connection()
    row = conn.execute(
        "SELECT created_at, payload_json FROM digests ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()

    if not row:
        return "<p>No digest built yet. Run dedup.py then summarize.py.</p>"

    created_at, payload_json = row
    payload = json.loads(payload_json)

    html = [f"<h1>Digest — {created_at}</h1>", "<h2>Top 10</h2>", "<ol>"]
    for story in payload.get("top10", []):
        links = " &middot; ".join(
            f'<a href="{l["link"]}">{l["source"]}</a>' for l in story["links"]
        )
        html.append(f"<li><strong>{story['title']}</strong><br>{story['summary']}<br>{links}</li>")
    html.append("</ol>")

    html.append("<h2>Also today</h2><ul>")
    for story in payload.get("rest", []):
        links = " &middot; ".join(
            f'<a href="{l["link"]}">{l["source"]}</a>' for l in story["links"]
        )
        html.append(f"<li>{story['title']} — {links}</li>")
    html.append("</ul>")

    return "\n".join(html)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
