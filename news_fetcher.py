"""
news_fetcher.py (v4.1 — yfinance bug fixes)

Bug fixes from logs:
1. "'<' not supported between str and float" — providerPublishTime sometimes returns
   as a string from Yahoo's API. Fixed with safe int() conversion.
2. Some tickers returning 0 articles — yfinance .news changed response format in
   newer versions. Now handles BOTH old format and new nested "content" format.
3. Added get_news() method as fallback alongside .news property.
"""

import time
import logging
import yfinance as yf
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


def get_yf_symbol(stock: dict) -> str:
    """Convert stock config to Yahoo Finance symbol. NSE → .NS, BSE → .BO"""
    ticker   = stock["ticker"].upper()
    exchange = stock.get("exchange", "NSE").upper()
    suffix   = ".BO" if exchange == "BSE" else ".NS"
    return f"{ticker}{suffix}"


def safe_timestamp(val) -> float:
    """
    Safely convert providerPublishTime to float.
    Yahoo Finance sometimes returns it as string, int, or float — handle all.
    This fixes: '<' not supported between instances of 'str' and 'float'
    """
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def parse_news_item(item: dict) -> dict | None:
    """
    Parse a single yfinance news item.
    Handles both old format (flat) and new format (nested under 'content').
    Returns None if item has no usable title.
    """
    # ── New yfinance format (nested under 'content') ──────────────────────────
    if "content" in item and isinstance(item["content"], dict):
        c      = item["content"]
        title  = c.get("title", "")
        link   = c.get("canonicalUrl", {}).get("url", "") or c.get("clickThroughUrl", {}).get("url", "")
        source = c.get("provider", {}).get("displayName", "Yahoo Finance")
        pub_ts = safe_timestamp(c.get("pubDate", 0))

        # pubDate in new format is ISO string like "2026-03-16T10:30:00Z"
        if isinstance(c.get("pubDate"), str) and "T" in str(c.get("pubDate", "")):
            try:
                dt = datetime.fromisoformat(c["pubDate"].replace("Z", "+00:00"))
                pub_ts = dt.timestamp()
            except Exception:
                pub_ts = 0.0

    # ── Old yfinance format (flat dict) ──────────────────────────────────────
    else:
        title  = item.get("title", "")
        link   = item.get("link", "")
        source = item.get("publisher", "Yahoo Finance")
        pub_ts = safe_timestamp(item.get("providerPublishTime", 0))

    if not title:
        return None

    published = (
        datetime.fromtimestamp(pub_ts, tz=timezone.utc).isoformat()
        if pub_ts > 0 else "Unknown"
    )

    return {
        "source":    source,
        "title":     title,
        "summary":   "",
        "link":      link,
        "published": published,
        "pub_ts":    pub_ts,  # keep for cutoff filtering
    }


def fetch_yfinance_news(stock: dict, lookback_hours: int = 24) -> list[dict]:
    """
    Fetch news via yfinance. Handles both .news property and get_news() method.
    Filters to only articles within the lookback window.
    """
    symbol    = get_yf_symbol(stock)
    ticker    = stock["ticker"]
    cutoff_ts = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).timestamp()

    try:
        yf_ticker = yf.Ticker(symbol)

        # Try .news property first, fall back to get_news()
        news_items = []
        try:
            news_items = yf_ticker.news or []
        except Exception:
            pass

        if not news_items:
            try:
                news_items = yf_ticker.get_news() or []
            except Exception:
                pass

        if not news_items:
            logger.info(f"  [{ticker}] yfinance ({symbol}): 0 articles returned by Yahoo")
            return []

        articles = []
        for item in news_items:
            parsed = parse_news_item(item)
            if not parsed:
                continue

            # Filter by time window — skip if pub_ts unknown (keep it)
            if parsed["pub_ts"] > 0 and parsed["pub_ts"] < cutoff_ts:
                continue

            # Remove internal key before returning
            parsed.pop("pub_ts", None)
            articles.append(parsed)

        logger.info(f"  [{ticker}] yfinance ({symbol}): {len(articles)} articles in last {lookback_hours}h")
        return articles

    except Exception as e:
        logger.warning(f"  [{ticker}] yfinance error for {symbol}: {e}")
        return []


def fetch_all_news(stock: dict, lookback_hours: int = 24) -> list[dict]:
    """Main entry. Fetches, deduplicates, adds polite delay."""
    articles = fetch_yfinance_news(stock, lookback_hours)
    time.sleep(0.5)

    seen, unique = set(), []
    for a in articles:
        key = a["title"][:60].lower().strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(a)

    logger.info(f"  [{stock['ticker']}] Final: {len(unique)} unique articles")
    return unique
