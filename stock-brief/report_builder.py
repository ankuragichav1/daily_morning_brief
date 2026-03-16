"""
report_builder.py
Builds a beautiful HTML email report from stock analyses.
"""

from datetime import datetime
import pytz

SENTIMENT_CONFIG = {
    "BULLISH":  {"color": "#00c851", "bg": "#e8fff1", "border": "#00c851", "icon": "▲", "label": "BULLISH"},
    "BEARISH":  {"color": "#ff4444", "bg": "#fff1f1", "border": "#ff4444", "icon": "▼", "label": "BEARISH"},
    "NEUTRAL":  {"color": "#ff8800", "bg": "#fff8ee", "border": "#ff8800", "icon": "◆", "label": "NEUTRAL"},
    "NO_NEWS":  {"color": "#888888", "bg": "#f5f5f5", "border": "#cccccc", "icon": "—",  "label": "NO NEWS"},
}

IMPACT_COLORS = {
    "POSITIVE": "#00c851",
    "NEGATIVE": "#ff4444",
    "NEUTRAL":  "#ff8800",
}

IMPORTANCE_BADGE = {
    "HIGH":   ("🔴", "#ff4444"),
    "MEDIUM": ("🟡", "#ff8800"),
    "LOW":    ("🟢", "#00c851"),
}


def _sentiment_summary_bar(analyses: list[dict]) -> str:
    counts = {"BULLISH": 0, "BEARISH": 0, "NEUTRAL": 0, "NO_NEWS": 0}
    for a in analyses:
        counts[a.get("overall_sentiment", "NO_NEWS")] += 1

    total = len(analyses)
    items = ""
    for sentiment, count in counts.items():
        if count == 0:
            continue
        cfg = SENTIMENT_CONFIG[sentiment]
        pct = int((count / total) * 100)
        items += f"""
        <div style="display:inline-block; margin-right:20px; text-align:center;">
          <div style="font-size:28px; font-weight:700; color:{cfg['color']};">{count}</div>
          <div style="font-size:11px; color:#666; letter-spacing:1px; text-transform:uppercase;">{cfg['label']}</div>
        </div>"""
    return items


def _stock_card(analysis: dict) -> str:
    sentiment = analysis.get("overall_sentiment", "NO_NEWS")
    strength = analysis.get("sentiment_strength", "")
    cfg = SENTIMENT_CONFIG.get(sentiment, SENTIMENT_CONFIG["NO_NEWS"])

    # Key events
    events_html = ""
    for event in analysis.get("key_events", []):
        imp_icon, imp_color = IMPORTANCE_BADGE.get(event.get("importance", "LOW"), ("🟢", "#00c851"))
        impact_color = IMPACT_COLORS.get(event.get("impact", "NEUTRAL"), "#888")
        events_html += f"""
        <tr>
          <td style="padding:6px 8px; font-size:13px; color:#333;">{imp_icon} {event.get('event','')}</td>
          <td style="padding:6px 8px; font-size:11px; font-weight:600; color:{impact_color}; white-space:nowrap; text-align:right;">
            {event.get('impact','')}
          </td>
        </tr>"""

    events_section = ""
    if events_html:
        events_section = f"""
        <table style="width:100%; border-collapse:collapse; margin:12px 0; background:#fafafa; border-radius:6px; overflow:hidden;">
          <thead>
            <tr style="background:#f0f0f0;">
              <th style="padding:6px 8px; font-size:11px; color:#888; text-align:left; font-weight:600; letter-spacing:1px;">EVENT</th>
              <th style="padding:6px 8px; font-size:11px; color:#888; text-align:right; font-weight:600; letter-spacing:1px;">IMPACT</th>
            </tr>
          </thead>
          <tbody>{events_html}</tbody>
        </table>"""

    # What to watch
    watch_items = "".join(
        f'<li style="margin:4px 0; font-size:13px; color:#555;">{w}</li>'
        for w in analysis.get("what_to_watch", [])
    )
    watch_section = f'<ul style="margin:8px 0; padding-left:20px;">{watch_items}</ul>' if watch_items else ""

    strength_badge = f'<span style="font-size:10px; background:{cfg["color"]}22; color:{cfg["color"]}; padding:2px 8px; border-radius:20px; margin-left:8px; font-weight:600; letter-spacing:1px;">{strength}</span>' if strength and strength != "N/A" else ""

    news_count = analysis.get("news_count", 0)
    news_badge_color = "#888" if news_count == 0 else "#333"

    return f"""
    <div style="border:1px solid {cfg['border']}; border-left:4px solid {cfg['border']}; border-radius:8px;
                background:{cfg['bg']}; margin-bottom:20px; overflow:hidden;">

      <!-- Header -->
      <div style="padding:14px 18px; border-bottom:1px solid {cfg['border']}33; display:flex; justify-content:space-between; align-items:center;">
        <div>
          <span style="font-size:18px; font-weight:700; color:#111; font-family:'Georgia', serif;">
            {analysis.get('company_name','')}
          </span>
          <span style="font-size:11px; color:#888; margin-left:8px; font-family:monospace;">
            {analysis.get('ticker','')}
          </span>
        </div>
        <div style="text-align:right;">
          <span style="font-size:20px; color:{cfg['color']};">{cfg['icon']}</span>
          <span style="font-size:13px; font-weight:700; color:{cfg['color']}; margin-left:6px;">{cfg['label']}</span>
          {strength_badge}
        </div>
      </div>

      <!-- Body -->
      <div style="padding:14px 18px;">

        <!-- Impact Summary -->
        <p style="font-size:14px; color:#333; line-height:1.6; margin:0 0 12px 0; font-style:italic;">
          {analysis.get('stock_impact_summary', '')}
        </p>

        {events_section}

        <!-- Analyst Note -->
        <div style="background:#fffbe6; border-left:3px solid #f0a500; padding:10px 14px; border-radius:4px; margin:12px 0;">
          <span style="font-size:11px; color:#f0a500; font-weight:700; letter-spacing:1px;">💡 ANALYST NOTE</span>
          <p style="font-size:13px; color:#555; margin:4px 0 0 0; line-height:1.5;">
            {analysis.get('analyst_note', '')}
          </p>
        </div>

        <!-- Watch List -->
        {"<div style='margin-top:10px;'><span style='font-size:11px; color:#888; font-weight:600; letter-spacing:1px;'>👁 WATCH FOR</span>" + watch_section + "</div>" if watch_section else ""}

        <!-- Footer -->
        <div style="margin-top:12px; font-size:11px; color:#aaa; text-align:right;">
          {news_count} news source{"s" if news_count != 1 else ""} analysed
        </div>
      </div>
    </div>"""


def build_html_report(analyses: list[dict]) -> str:
    ist = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(ist)
    date_str = now_ist.strftime("%A, %d %B %Y")
    time_str = now_ist.strftime("%I:%M %p IST")

    summary_bar = _sentiment_summary_bar(analyses)
    stock_cards = "".join(_stock_card(a) for a in analyses)

    bullish = sum(1 for a in analyses if a.get("overall_sentiment") == "BULLISH")
    bearish = sum(1 for a in analyses if a.get("overall_sentiment") == "BEARISH")

    if bullish > bearish:
        market_mood = "🟢 Portfolio leaning <strong>positive</strong> today"
    elif bearish > bullish:
        market_mood = "🔴 Portfolio facing <strong>headwinds</strong> today"
    else:
        market_mood = "🟡 Portfolio in <strong>mixed/neutral</strong> territory"

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Portfolio Morning Brief — {date_str}</title>
</head>
<body style="margin:0; padding:0; background:#f0f2f5; font-family:'Helvetica Neue', Helvetica, Arial, sans-serif;">

  <div style="max-width:680px; margin:0 auto; background:#f0f2f5; padding:24px 16px;">

    <!-- Header -->
    <div style="background:linear-gradient(135deg, #0f2027, #203a43, #2c5364); border-radius:12px;
                padding:28px 30px; margin-bottom:20px; color:white;">
      <div style="font-size:11px; letter-spacing:3px; text-transform:uppercase; color:#7ecef4; margin-bottom:6px;">
        Daily Portfolio Intelligence
      </div>
      <div style="font-size:26px; font-weight:700; color:#ffffff; margin-bottom:4px; font-family:'Georgia', serif;">
        Morning Brief
      </div>
      <div style="font-size:13px; color:#a8d8ea;">
        {date_str} &nbsp;·&nbsp; {time_str}
      </div>

      <!-- Summary counts -->
      <div style="margin-top:20px; padding-top:20px; border-top:1px solid rgba(255,255,255,0.15);">
        {summary_bar}
      </div>

      <!-- Mood line -->
      <div style="margin-top:16px; font-size:13px; color:#ddeeff;">
        {market_mood}
      </div>
    </div>

    <!-- Stock Cards -->
    {stock_cards}

    <!-- Footer -->
    <div style="text-align:center; padding:20px; font-size:11px; color:#aaa; line-height:1.8;">
      <strong>Saatvik Portfolio Tracker</strong> · Powered by Groq LLaMA3 + Google News<br>
      This report is AI-generated for informational purposes only.<br>
      Not SEBI registered advice. Do your own research before investing.
    </div>

  </div>
</body>
</html>"""


def build_subject_line(analyses: list[dict]) -> str:
    bullish = [a["ticker"] for a in analyses if a.get("overall_sentiment") == "BULLISH"]
    bearish = [a["ticker"] for a in analyses if a.get("overall_sentiment") == "BEARISH"]
    ist = pytz.timezone("Asia/Kolkata")
    date_str = datetime.now(ist).strftime("%d %b")

    parts = []
    if bullish:
        parts.append(f"▲ {', '.join(bullish[:2])}")
    if bearish:
        parts.append(f"▼ {', '.join(bearish[:2])}")
    if not parts:
        parts.append("All Quiet")

    return f"📊 Morning Brief [{date_str}] — {' | '.join(parts)}"
