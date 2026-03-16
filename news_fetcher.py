"""
news_fetcher.py  (v3 — Finnhub + Marketaux)
Both APIs are confirmed to work from GitHub Actions servers.

WHY previous versions failed:
  v1 (RSS)     — GitHub Actions blocks RSS/scraping silently
  v2 (NewsAPI) — Free tier is "Developer" plan = localhost only (HTTP 426 from servers)

FREE API KEYS NEEDED:
  FINNHUB_API_KEY  — https://finnhub.io/register (free, 60 calls/min)
  MARKETAUX_KEY    — https://www.marketaux.com/register (free, 100/day, backup only)

Add both as GitHub Secrets.
"""

import os
import time
import logging
import requests
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "PortfolioMorningBrief/3.0"})

FINNHUB_BASE  = "https://finnhub.io/api/v1"
MARKETAUX_BASE = "https://api.marketaux.com/v1/news/all"


def get_cutoff_unix(lookback_hours: int) -> int:
    """Return UNIX timestamp for cutoff time (Finnhub uses UNIX timestamps)."""
    return int((datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).timestamp())


def get_cutoff_iso(lookback_hours: int) -> str:
    """Return ISO date string for cutoff (Marketaux format)."""
    dt = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    return dt.strftime("%Y-%m-%dT%H:%M")


# ── Finnhub ────────────────────────────────────────────────────────────────────

def fetch_finnhub(stock: dict, lookback_hours: int = 24) -> list[dict]:
    """
    Finnhub company news API.
    Works from GitHub Actions. Free: 60 calls/min.
    Uses NSE:/BSE: prefix for Indian stocks.
    """
    api_key = os.environ.get("FINNHUB_API_KEY", "")
    if not api_key:
        logger.warning("FINNHUB_API_KEY not set — skipping Finnhub")
        return []

    # Build symbol with exchange prefix
    exchange = stock.get("exchange", "NSE").upper()
    ticker   = stock["ticker"].upper()
    symbol   = f"{exchange}:{ticker}"

    today     = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    from_date = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).strftime("%Y-%m-%d")

    params = {
        "symbol": symbol,
        "from":   from_date,
        "to":     today,
        "token":  api_key,
    }

    try:
        resp = SESSION.get(f"{FINNHUB_BASE}/company-news", params=params, timeout=15)
        resp.raise_for_status()
        items = resp.json()

        if not isinstance(items, list):
            logger.warning(f"  [{ticker}] Finnhub unexpected response: {items}")
            return []

        cutoff_unix = get_cutoff_unix(lookback_hours)
        articles = []
        for item in items:
            if item.get("datetime", 0) < cutoff_unix:
                continue
            articles.append({
                "source":    item.get("source", "Finnhub"),
                "title":     item.get("headline", ""),
                "summary":   item.get("summary", ""),
                "link":      item.get("url", ""),
                "published": datetime.fromtimestamp(
                    item.get("datetime", 0), tz=timezone.utc
                ).isoformat(),
            })

        logger.info(f"  [{ticker}] Finnhub: {len(articles)} articles")
        return articles

    except requests.HTTPError as e:
        status = e.response.status_code if e.response else "?"
        logger.warning(f"  [{ticker}] Finnhub HTTP {status}: {e}")
        return []
    except Exception as e:
        logger.warning(f"  [{ticker}] Finnhub error: {e}")
        return []


def fetch_finnhub_by_keywords(stock: dict, lookback_hours: int = 24) -> list[dict]:
    """
    Fallback: Finnhub general market news filtered by company keywords.
    Used when symbol-based lookup returns 0 (e.g. BSE-only stocks).
    """
    api_key = os.environ.get("FINNHUB_API_KEY", "")
    if not api_key:
        return []

    params = {"category": "general", "token": api_key}
    cutoff_unix = get_cutoff_unix(lookback_hours)
    keywords = [kw.lower() for kw in stock.get("keywords", [stock["name"]])]

    try:
        resp = SESSION.get(f"{FINNHUB_BASE}/news", params=params, timeout=15)
        resp.raise_for_status()
        items = resp.json()

        articles = []
        for item in items:
            if item.get("datetime", 0) < cutoff_unix:
                continue
            text = (item.get("headline", "") + " " + item.get("summary", "")).lower()
            if any(kw in text for kw in keywords):
                articles.append({
                    "source":    item.get("source", "Finnhub"),
                    "title":     item.get("headline", ""),
                    "summary":   item.get("summary", ""),
                    "link":      item.get("url", ""),
                    "published": datetime.fromtimestamp(
                        item.get("datetime", 0), tz=timezone.utc
                    ).isoformat(),
                })

        logger.info(f"  [{stock['ticker']}] Finnhub keyword search: {len(articles)} articles")
        return articles

    except Exception as e:
        logger.warning(f"  [{stock['ticker']}] Finnhub keyword search error: {e}")
        return []


# ── Marketaux ──────────────────────────────────────────────────────────────────

def fetch_marketaux(stock: dict, lookback_hours: int = 24) -> list[dict]:
    """
    Marketaux financial news API.
    Works from GitHub Actions. Free: 100 requests/day.
    Used as backup when Finnhub returns 0.
    """
    api_key = os.environ.get("MARKETAUX_KEY", "")
    if not api_key:
        logger.debug("MARKETAUX_KEY not set — skipping Marketaux")
        return []

    # Search by company name keywords
    search_terms = " OR ".join(stock.get("keywords", [stock["name"]])[:2])

    params = {
        "search":        search_terms,
        "language":      "en",
        "published_after": get_cutoff_iso(lookback_hours),
        "limit":         5,
        "api_token":     api_key,
    }

    try:
        resp = SESSION.get(MARKETAUX_BASE, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        articles = []
        for item in data.get("data", []):
            articles.append({
                "source":    item.get("source", "Marketaux"),
                "title":     item.get("title", ""),
                "summary":   item.get("description", ""),
                "link":      item.get("url", ""),
                "published": item.get("published_at", ""),
            })

        logger.info(f"  [{stock['ticker']}] Marketaux: {len(articles)} articles")
        return articles

    except requests.HTTPError as e:
        status = e.response.status_code if e.response else "?"
        logger.warning(f"  [{stock['ticker']}] Marketaux HTTP {status}: {e}")
        return []
    except Exception as e:
        logger.warning(f"  [{stock['ticker']}] Marketaux error: {e}")
        return []


# ── Main entry ─────────────────────────────────────────────────────────────────

def fetch_all_news(stock: dict, lookback_hours: int = 24) -> list[dict]:
    """
    Fetch from Finnhub (primary) → Finnhub keyword search → Marketaux (backup).
    Deduplicates by title.
    """
    all_articles = []

    # 1. Finnhub by symbol (most precise)
    all_articles = fetch_finnhub(stock, lookback_hours)

    # 2. If no results, try Finnhub general news filtered by keyword
    if not all_articles:
        all_articles = fetch_finnhub_by_keywords(stock, lookback_hours)

    # 3. If still nothing, try Marketaux
    if not all_articles:
        all_articles = fetch_marketaux(stock, lookback_hours)
        time.sleep(0.3)  # Polite delay for Marketaux rate limit

    # Deduplicate by title
    seen = set()
    unique = []
    for a in all_articles:
        key = a["title"][:60].lower().strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(a)

    logger.info(f"  [{stock['ticker']}] Final: {len(unique)} unique articles")
    return unique
