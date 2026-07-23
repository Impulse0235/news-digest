import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import yaml

from db import get_connection
from email_template import render_alert_html

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
ALERTS_CONFIG = os.environ.get("ALERTS_CONFIG", "/app/config/alerts.yaml")


def load_terms():
    with open(ALERTS_CONFIG) as f:
        cfg = yaml.safe_load(f) or {}
    keywords = cfg.get("keywords", []) or []
    breaking_terms = cfg.get("breaking_terms", []) or []
    # Simple substring matching, per your choice — both lists are treated
    # identically, any hit on either one triggers an alert.
    return [t.lower() for t in keywords + breaking_terms]


def find_matches(title, terms):
    title_lower = title.lower()
    return [t for t in terms if t in title_lower]


def send_alert_email(matches):
    sender = os.environ["SENDER_EMAIL"]
    recipient = os.environ["RECIPIENT_EMAIL"]

    html = render_alert_html(matches)
    story_word = "alert" if len(matches) == 1 else "alerts"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🚨 {len(matches)} {story_word} — News Digest"
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(os.environ["SMTP_LOGIN"], os.environ["SMTP_PASSWORD"])
        server.sendmail(sender, [recipient], msg.as_string())


def check_alerts():
    terms = load_terms()
    if not terms:
        print("[alert_check] No keywords or breaking terms configured — nothing to check")
        return

    conn = get_connection()
    rows = conn.execute(
        "SELECT id, title, link, source FROM items WHERE alert_checked = 0"
    ).fetchall()

    if not rows:
        print("[alert_check] No new items to check")
        conn.close()
        return

    matches = []
    matched_ids = []
    all_ids = []

    for item_id, title, link, source in rows:
        all_ids.append(item_id)
        hits = find_matches(title, terms)
        if hits:
            matches.append({"title": title, "link": link, "source": source, "matched_terms": hits})
            matched_ids.append(item_id)

    if matches:
        send_alert_email(matches)

    conn.executemany("UPDATE items SET alert_checked = 1 WHERE id = ?", [(i,) for i in all_ids])
    if matched_ids:
        conn.executemany("UPDATE items SET alerted = 1 WHERE id = ?", [(i,) for i in matched_ids])
    conn.commit()
    conn.close()

    summary = f"[alert_check] Checked {len(all_ids)} item(s), {len(matches)} match(es)"
    if matches:
        summary += f" — alert sent to {os.environ['RECIPIENT_EMAIL']}"
    print(summary)


if __name__ == "__main__":
    check_alerts()
