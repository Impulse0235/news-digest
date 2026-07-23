import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from db import get_connection
from email_template import render_digest_html

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))


def load_latest_unsent():
    conn = get_connection()
    row = conn.execute(
        "SELECT id, created_at, payload_json FROM digests WHERE sent = 0 ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return row


def send_email(subject, html_body):
    sender = os.environ["SENDER_EMAIL"]
    recipient = os.environ["RECIPIENT_EMAIL"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(os.environ["SMTP_LOGIN"], os.environ["SMTP_PASSWORD"])
        server.sendmail(sender, [recipient], msg.as_string())


def send_digest():
    row = load_latest_unsent()
    if not row:
        print("[email_digest] No un-sent digest found — nothing to send")
        return

    digest_id, created_at, payload_json = row
    payload = json.loads(payload_json)

    html = render_digest_html(created_at, payload)
    subject = f"News Digest — {created_at[:10]}"

    send_email(subject, html)

    # Mark this digest, and any older un-sent backlog, as sent — avoids
    # re-sending stale digests if this script is ever run more than once
    # before the next one is built.
    conn = get_connection()
    conn.execute("UPDATE digests SET sent = 1 WHERE sent = 0")
    conn.commit()
    conn.close()

    print(f"[email_digest] Sent digest #{digest_id} to {os.environ['RECIPIENT_EMAIL']}")


if __name__ == "__main__":
    send_digest()
