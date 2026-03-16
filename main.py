"""
main.py
Orchestrates the daily portfolio morning brief.
Run manually: python main.py
Scheduled via: GitHub Actions (see .github/workflows/daily_brief.yml)
"""

import yaml
import logging
import sys
import os
from datetime import datetime
import pytz

from news_fetcher import fetch_all_news
from groq_analyser import analyse_stock
from report_builder import build_html_report, build_subject_line
from email_sender import send_report

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def main():
    logger.info("=" * 60)
    logger.info("📊 PORTFOLIO MORNING BRIEF — STARTING")
    logger.info("=" * 60)

    # Load config
    config = load_config()
    portfolio   = config["portfolio"]
    settings    = config["settings"]
    lookback_h  = settings.get("report_date_lookback_hours", 24)
    groq_model  = settings.get("groq_model", "llama3-70b-8192")

    ist = pytz.timezone("Asia/Kolkata")
    logger.info(f"Time (IST): {datetime.now(ist).strftime('%d %b %Y %I:%M %p')}")
    logger.info(f"Stocks in portfolio: {len(portfolio)}")
    logger.info(f"Lookback window: {lookback_h} hours")
    logger.info(f"LLM model: {groq_model}")
    logger.info("-" * 60)

    analyses = []

    for stock in portfolio:
        logger.info(f"\n🔍 Processing: {stock['name']} ({stock['ticker']})")

        # Step 1: Fetch news
        articles = fetch_all_news(stock, lookback_hours=lookback_h)

        # Step 2: Analyse with Groq
        analysis = analyse_stock(stock, articles, model=groq_model)
        analyses.append(analysis)

    logger.info("\n" + "-" * 60)
    logger.info("📝 Building HTML report...")

    # Step 3: Build report
    html = build_html_report(analyses)
    subject = build_subject_line(analyses)

    logger.info(f"Subject: {subject}")

    # Step 4: Send email
    logger.info("📧 Sending email...")
    send_report(subject, html)

    # Step 5: Optionally save report locally (useful for debugging)
    if os.environ.get("SAVE_REPORT_LOCAL", "false").lower() == "true":
        fname = f"report_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
        with open(fname, "w") as f:
            f.write(html)
        logger.info(f"💾 Report saved locally: {fname}")

    logger.info("\n✅ Morning brief complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)
