"""
news_fetcher.py (v4.3)
Changes:
- Added raw count logging before time filter (shows Yahoo IS returning articles)
- lookback_hours now driven by config (set to 168 = 7 days for testing)
- Clearer log messages distinguishing "Yahoo returned 0" vs "filtered by time"
"""

import time
import logging
import yfinance as yf
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


def get_yf_symbol(stock: dict) -> str:
    ticker   = stock["ticker"].upper()
    exchange = stock.get("exchange", "NSE").upper()
    suffix   = ".BO" if exchange == "BSE" else ".NS"
    return f"{ticker}{suffix}"


def safe_timestamp(val) -> float:
    """Safely convert providerPublishTime to float regardless of type."""
    if isinstance(val, str):
        # Try ISO format e.g. "2026-03-16T10:30:00Z"
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00")).timestamp()
        except Exception:
            pass
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def parse_news_item(item: dict) -> dict | None:
    """
    Parse a yfinance news item — handles both old (flat) and new (nested) formats.
    Returns None if no usable title found.
    """
    # ── New format: content nested under "content" key ────────────────────────
    if "content" in item and isinstance(item["content"], dict):
        c      = item["content"]
        title  = c.get("title", "")
        link   = (c.get("canonicalUrl") or {}).get("url", "") or \
                 (c.get("clickThroughUrl") or {}).get("url", "")
        source = (c.get("provider") or {}).get("displayName", "Yahoo Finance")
        pub_ts = safe_timestamp(c.get("pubDate", 0))

    # ── Old format: flat dict ─────────────────────────────────────────────────
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
        "pub_ts":    pub_ts,
    }


def fetch_yfinance_news(stock: dict, lookback_hours: int = 168) -> list[dict]:
    symbol    = get_yf_symbol(stock)
    ticker    = stock["ticker"]
    cutoff_ts = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).timestamp()
    cutoff_dt = datetime.fromtimestamp(cutoff_ts, tz=timezone.utc).strftime("%Y-%m-%d")

    try:
        yf_ticker  = yf.Ticker(symbol)
        news_items = []

        try:
            news_items = yf_ticker.news or []
        except Exception as e:
            logger.debug(f"  [{ticker}] .news failed: {e}")

        if not news_items:
            try:
                news_items = yf_ticker.get_news() or []
            except Exception as e:
                logger.debug(f"  [{ticker}] .get_news() failed: {e}")

        raw_count = len(news_items)

        if raw_count == 0:
            logger.info(f"  [{ticker}] Yahoo Finance returned 0 articles for {symbol}")
            return []

        # Log raw count BEFORE filtering so we can see what Yahoo returned
        logger.info(f"  [{ticker}] Yahoo raw: {raw_count} articles for {symbol} — filtering to last {lookback_hours}h (since {cutoff_dt})")

        articles = []
        skipped_old = 0
        skipped_no_title = 0

        for item in news_items:
            parsed = parse_news_item(item)
            if not parsed:
                skipped_no_title += 1
                continue
            if parsed["pub_ts"] > 0 and parsed["pub_ts"] < cutoff_ts:
                skipped_old += 1
                continue
            parsed.pop("pub_ts", None)
            articles.append(parsed)

        logger.info(f"  [{ticker}] After filter: {len(articles)} kept | {skipped_old} too old | {skipped_no_title} no title")
        return articles

    except Exception as e:
        logger.warning(f"  [{ticker}] yfinance error for {symbol}: {e}")
        return []


def fetch_all_news(stock: dict, lookback_hours: int = 168) -> list[dict]:
    """Main entry. Default 168h (7 days) for testing."""
    articles = fetch_yfinance_news(stock, lookback_hours)
    time.sleep(0.5)

    seen, unique = set(), []
    for a in articles:
        key = a["title"][:60].lower().strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(a)

    logger.info(f"  [{stock['ticker']}] Final unique: {len(unique)}")
    return unique
