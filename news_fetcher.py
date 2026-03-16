"""
news_fetcher.py (v4 — yfinance)
Uses Yahoo Finance via yfinance library.
- No API key needed
- Confirmed coverage for NSE/BSE Indian stocks
- Works from GitHub Actions
- Suffix: TICKER.NS for NSE, TICKER.BO for BSE
"""

import time
import logging
import yfinance as yf
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


def get_yf_symbol(stock: dict) -> str:
    """Convert stock config to Yahoo Finance symbol format."""
    ticker   = stock["ticker"].upper()
    exchange = stock.get("exchange", "NSE").upper()
    suffix   = ".BO" if exchange == "BSE" else ".NS"
    return f"{ticker}{suffix}"


def fetch_yfinance_news(stock: dict, lookback_hours: int = 24) -> list[dict]:
    """
    Fetch news via yfinance ticker.news
    No API key required. Works from GitHub Actions.
    Confirmed to cover NSE/BSE Indian stocks.
    """
    symbol    = get_yf_symbol(stock)
    ticker    = stock["ticker"]
    cutoff_ts = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).timestamp()

    try:
        yf_ticker  = yf.Ticker(symbol)
        news_items = yf_ticker.news

        if not news_items:
            logger.info(f"  [{ticker}] yfinance ({symbol}): 0 articles")
            return []

        articles = []
        for item in news_items:
            # Handle both old and new yfinance response formats
            title  = item.get("title", "")
            link   = item.get("link", "")
            source = item.get("publisher", "Yahoo Finance")
            pub_ts = item.get("providerPublishTime", 0)

            # New yfinance format nests inside "content"
            if not title and "content" in item:
                c      = item["content"]
                title  = c.get("title", "")
                link   = c.get("canonicalUrl", {}).get("url", "")
                source = c.get("provider", {}).get("displayName", "Yahoo Finance")
                pub_ts = c.get("pubDate", pub_ts)

            if not title:
                continue
            if pub_ts and pub_ts < cutoff_ts:
                continue  # older than lookback window

            published = (
                datetime.fromtimestamp(pub_ts, tz=timezone.utc).isoformat()
                if pub_ts else "Unknown"
            )

            articles.append({
                "source":    source,
                "title":     title,
                "summary":   "",
                "link":      link,
                "published": published,
            })

        logger.info(f"  [{ticker}] yfinance ({symbol}): {len(articles)} articles")
        return articles

    except Exception as e:
        logger.warning(f"  [{ticker}] yfinance error for {symbol}: {e}")
        return []


def fetch_all_news(stock: dict, lookback_hours: int = 24) -> list[dict]:
    """Main entry point. Fetches from Yahoo Finance, deduplicates."""
    articles = fetch_yfinance_news(stock, lookback_hours)
    time.sleep(0.5)  # Be gentle with Yahoo's unofficial API

    seen, unique = set(), []
    for a in articles:
        key = a["title"][:60].lower().strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(a)

    logger.info(f"  [{stock['ticker']}] Final: {len(unique)} unique articles")
    return unique
