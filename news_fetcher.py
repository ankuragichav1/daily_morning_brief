"""
news_fetcher.py  (v2 — Fixed for GitHub Actions)
Uses NewsAPI.org + GNews API instead of RSS feeds.
Both work reliably from GitHub Actions runners.

Free tier limits:
  NewsAPI : 100 requests/day  → https://newsapi.org/register
  GNews   : 100 requests/day  → https://gnews.io/

Set these env vars / GitHub Secrets:
  NEWS_API_KEY   — from newsapi.org
  GNEWS_API_KEY  — from gnews.io (optional fallback)
"""

import os
import requests
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

NEWS_API_BASE  = "https://newsapi.org/v2/everything"
GNEWS_API_BASE = "https://gnews.io/api/v4/search"

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "PortfolioMorningBrief/2.0"})


def get_cutoff_time(lookback_hours: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=lookback_hours)


def fetch_newsapi(stock: dict, lookback_hours: int = 24) -> list[dict]:
    """
    Fetch from NewsAPI.org — most reliable, works from GitHub Actions.
    Requires NEWS_API_KEY env var.
    """
    api_key = os.environ.get("NEWS_API_KEY", "")
    if not api_key:
        logger.warning("NEWS_API_KEY not set — skipping NewsAPI")
        return []

    cutoff = get_cutoff_time(lookback_hours)
    from_date = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Build query: company name + top keywords
    name = stock["name"]
    kws  = stock.get("keywords", [])[:2]
    query_parts = [f'"{name}"'] + kws
    query = " OR ".join(query_parts)

    params = {
        "q":        query,
        "from":     from_date,
        "sortBy":   "publishedAt",
        "language": "en",
        "pageSize": 10,
        "apiKey":   api_key,
    }

    try:
        resp = SESSION.get(NEWS_API_BASE, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        articles = []
        for item in data.get("articles", []):
            articles.append({
                "source":    item.get("source", {}).get("name", "NewsAPI"),
                "title":     item.get("title", ""),
                "summary":   item.get("description", "") or item.get("content", "")[:300],
                "link":      item.get("url", ""),
                "published": item.get("publishedAt", ""),
            })

        logger.info(f"  [{stock['ticker']}] NewsAPI: {len(articles)} articles")
        return articles

    except requests.HTTPError as e:
        if e.response.status_code == 426:
            logger.warning(f"  [{stock['ticker']}] NewsAPI free tier limit hit")
        elif e.response.status_code == 401:
            logger.error("  NewsAPI: Invalid API key")
        else:
            logger.warning(f"  [{stock['ticker']}] NewsAPI HTTP error: {e}")
        return []
    except Exception as e:
        logger.warning(f"  [{stock['ticker']}] NewsAPI error: {e}")
        return []


def fetch_gnews(stock: dict, lookback_hours: int = 24) -> list[dict]:
    """
    Fetch from GNews.io — good fallback, also works from GitHub Actions.
    Requires GNEWS_API_KEY env var.
    """
    api_key = os.environ.get("GNEWS_API_KEY", "")
    if not api_key:
        logger.debug("GNEWS_API_KEY not set — skipping GNews")
        return []

    cutoff = get_cutoff_time(lookback_hours)
    from_date = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    name = stock["name"]
    kws  = stock.get("keywords", [])[:1]
    query = f'"{name}"' + (f' OR "{kws[0]}"' if kws else "")

    params = {
        "q":       query,
        "from":    from_date,
        "sortby":  "publishedAt",
        "lang":    "en",
        "max":     5,
        "token":   api_key,
    }

    try:
        resp = SESSION.get(GNEWS_API_BASE, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        articles = []
        for item in data.get("articles", []):
            articles.append({
                "source":    item.get("source", {}).get("name", "GNews"),
                "title":     item.get("title", ""),
                "summary":   item.get("description", ""),
                "link":      item.get("url", ""),
                "published": item.get("publishedAt", ""),
            })

        logger.info(f"  [{stock['ticker']}] GNews: {len(articles)} articles")
        return articles

    except Exception as e:
        logger.warning(f"  [{stock['ticker']}] GNews error: {e}")
        return []


def fetch_all_news(stock: dict, lookback_hours: int = 24) -> list[dict]:
    """Aggregate from all available sources, deduplicate by title."""
    all_articles = []

    # Primary source
    all_articles += fetch_newsapi(stock, lookback_hours)

    # Fallback if NewsAPI returned nothing
    if not all_articles:
        all_articles += fetch_gnews(stock, lookback_hours)

    # Deduplicate by title
    seen = set()
    unique = []
    for a in all_articles:
        key = a["title"][:60].lower().strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(a)

    logger.info(f"  [{stock['ticker']}] Total unique articles: {len(unique)}")
    return unique
