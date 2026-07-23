def render_alert_html(matches):
    rows = "".join(
        f"""
        <tr>
        <td style="padding:14px 18px; border-bottom:1px solid #f0f2f5;">
          <div style="font-size:11px; font-weight:700; color:#e63946; text-transform:uppercase; letter-spacing:0.5px;">
            Matched: {", ".join(m["matched_terms"])}
          </div>
          <div style="font-size:15px; font-weight:700; color:#1a1a1a; margin-top:4px;">{m['title']}</div>
          <div style="margin-top:6px;">
            <a href="{m['link']}" style="display:inline-block; font-size:12px; font-weight:600; color:#3a7bd5; text-decoration:none; background-color:#eaf2fc; padding:5px 12px; border-radius:20px;">{m['source']} ↗</a>
          </div>
        </td>
        </tr>
        """
        for m in matches
    )

    story_word = "story" if len(matches) == 1 else "stories"

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0; padding:0; background-color:#eef1f5; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#eef1f5; padding:24px 0;">
<tr><td align="center">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff; border-radius:16px; overflow:hidden; box-shadow:0 2px 12px rgba(0,0,0,0.06);">

<tr>
<td style="background:linear-gradient(135deg,#7a1f1f 0%,#b8322f 60%,#e63946 100%); padding:28px 32px;">
  <div style="font-size:13px; letter-spacing:2px; text-transform:uppercase; color:#ffd1d1; font-weight:600; margin-bottom:8px;">🚨 Instant Alert</div>
  <div style="font-size:22px; font-weight:700; color:#ffffff;">{len(matches)} matching {story_word} found</div>
</td>
</tr>

<tr><td><table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows}</table></td></tr>

<tr><td style="background-color:#f7f9fb; padding:18px 32px; text-align:center;">
  <div style="font-size:12px; color:#9aa5b1;">Matched against your configured keywords &middot; Checked every 30 minutes</div>
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""


CATEGORY_STYLES = {
    "world": ("🌍", "World & Geopolitics", "#e63946"),
    "security": ("⚓", "Security & Conflict", "#e63946"),
    "legal": ("⚖️", "Legal", "#8338ec"),
    "technology": ("💻", "Technology", "#06a77d"),
    "business": ("💼", "Business", "#f77f00"),
    "science": ("🔬", "Science", "#118ab2"),
    "health": ("🏥", "Health", "#ef476f"),
    "sports": ("🏆", "Sports", "#3a86ff"),
    "other": ("📰", "News", "#6c757d"),
}


def category_style(category):
    return CATEGORY_STYLES.get((category or "other").lower(), CATEGORY_STYLES["other"])


def render_links(links):
    return "".join(
        f'<a href="{l["link"]}" style="display:inline-block; font-size:12px; font-weight:600; '
        f'color:#3a7bd5; text-decoration:none; background-color:#eaf2fc; padding:5px 12px; '
        f'border-radius:20px; margin-right:6px;">{l["source"]} ↗</a>'
        for l in links
    )


def render_story_card(index, story):
    emoji, label, color = category_style(story.get("category"))
    return f"""
    <tr>
    <td style="padding:12px 32px;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-left:4px solid {color}; background-color:#fafbfc; border-radius:8px;">
        <tr>
          <td style="padding:16px 18px;">
            <table role="presentation" cellpadding="0" cellspacing="0"><tr>
              <td style="width:28px; height:28px; background-color:{color}; border-radius:50%; text-align:center; vertical-align:middle; color:#fff; font-size:13px; font-weight:700;">{index}</td>
              <td style="padding-left:10px; font-size:11px; font-weight:700; color:{color}; letter-spacing:0.5px; text-transform:uppercase;">{emoji} {label}</td>
            </tr></table>
            <div style="font-size:16px; font-weight:700; color:#1a1a1a; margin-top:10px; line-height:1.4;">{story['title']}</div>
            <div style="font-size:14px; color:#4a4a4a; margin-top:6px; line-height:1.5;">{story['summary']}</div>
            <div style="margin-top:10px;">{render_links(story['links'])}</div>
          </td>
        </tr>
      </table>
    </td>
    </tr>
    """


def render_rest_row(story, is_last):
    border = "" if is_last else "border-bottom:1px solid #f0f2f5;"
    links_html = "".join(
        f' <a href="{l["link"]}" style="color:#8a94a3; text-decoration:none; font-size:12px;"> — {l["source"]} ↗</a>'
        for l in story["links"]
    )
    return f"""
    <tr>
      <td style="padding:10px 0; {border} font-size:14px; color:#333;">
        {story['title']}{links_html}
      </td>
    </tr>
    """


def render_digest_html(created_at, payload, source_names=None):
    top10 = payload.get("top10", [])
    rest = payload.get("rest", [])

    cards = "".join(render_story_card(i + 1, story) for i, story in enumerate(top10))

    rest_rows = "".join(
        render_rest_row(story, i == len(rest) - 1) for i, story in enumerate(rest)
    )

    sources_line = source_names or "your configured feeds"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>News Digest</title>
</head>
<body style="margin:0; padding:0; background-color:#eef1f5; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#eef1f5; padding:24px 0;">
<tr><td align="center">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff; border-radius:16px; overflow:hidden; box-shadow:0 2px 12px rgba(0,0,0,0.06);">

<tr>
<td style="background:linear-gradient(135deg,#1e3a5f 0%,#2d5a8c 50%,#3a7bd5 100%); padding:36px 32px 28px 32px;">
  <div style="font-size:13px; letter-spacing:2px; text-transform:uppercase; color:#9fc4ec; font-weight:600; margin-bottom:8px;">🗞️ Your Morning Briefing</div>
  <div style="font-size:26px; font-weight:700; color:#ffffff; line-height:1.3;">News Digest</div>
  <div style="font-size:14px; color:#c7ddf5; margin-top:6px;">{created_at} &middot; {len(top10)} stories curated, {len(rest)} more inside</div>
</td>
</tr>

<tr><td style="padding:28px 32px 8px 32px;"><div style="font-size:12px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; color:#3a7bd5;">⭐ Top Stories</div></td></tr>

{cards}

<tr><td style="padding:20px 32px 4px 32px;"><div style="border-top:1px solid #e8ecf1;"></div></td></tr>

<tr><td style="padding:20px 32px 8px 32px;"><div style="font-size:12px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; color:#8a94a3;">📋 Also Today</div></td></tr>

<tr><td style="padding:0 32px 8px 32px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0">
{rest_rows}
</table></td></tr>

<tr><td style="background-color:#f7f9fb; padding:22px 32px; text-align:center;">
  <div style="font-size:12px; color:#9aa5b1;">Curated from {sources_line} &middot; Summarized by AI &middot; Sent every morning at 7am</div>
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""