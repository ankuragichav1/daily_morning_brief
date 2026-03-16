"""
news_fetcher.py
Fetches news from multiple free sources: Google News RSS, MoneyControl RSS, Economic Times RSS
No paid API required.
"""

import feedparser
import requests
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
import time
import logging

logger = logging.getLogger(__name__)


def get_cutoff_time(lookback_hours: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=lookback_hours)


def fetch_google_news_rss(keywords: list[str], lookback_hours: int = 24) -> list[dict]:
    """Fetch from Google News RSS — completely free, no API key needed."""
    cutoff = get_cutoff_time(lookback_hours)
    articles = []

    for keyword in keywords[:2]:  # Top 2 keywords to avoid rate limiting
        query = quote(f"{keyword} stock NSE BSE")
        url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

                if published and published < cutoff:
                    continue

                articles.append({
                    "source": "Google News",
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", ""),
                    "link": entry.get("link", ""),
                    "published": published.isoformat() if published else "Unknown",
                })
            time.sleep(1)  # Polite delay
        except Exception as e:
            logger.warning(f"Google News fetch failed for '{keyword}': {e}")

    return articles


def fetch_moneycontrol_rss(company_name: str, lookback_hours: int = 24) -> list[dict]:
    """Fetch from MoneyControl news RSS."""
    cutoff = get_cutoff_time(lookback_hours)
    articles = []
    query = quote(company_name)
    url = f"https://www.moneycontrol.com/rss/results.xml?query={query}"

    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:5]:
            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

            if published and published < cutoff:
                continue

            articles.append({
                "source": "MoneyControl",
                "title": entry.get("title", ""),
                "summary": entry.get("summary", ""),
                "link": entry.get("link", ""),
                "published": published.isoformat() if published else "Unknown",
            })
    except Exception as e:
        logger.warning(f"MoneyControl fetch failed for '{company_name}': {e}")

    return articles


def fetch_economic_times_rss(keywords: list[str], lookback_hours: int = 24) -> list[dict]:
    """Fetch from Economic Times Markets RSS feed."""
    cutoff = get_cutoff_time(lookback_hours)
    articles = []

    # ET Markets general feed — then filter by keyword
    url = "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms"
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = entry.get("title", "").lower()
            summary = entry.get("summary", "").lower()
            content = title + " " + summary

            # Only include if relevant to our stock
            if not any(kw.lower() in content for kw in keywords):
                continue

            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

            if published and published < cutoff:
                continue

            articles.append({
                "source": "Economic Times",
                "title": entry.get("title", ""),
                "summary": entry.get("summary", ""),
                "link": entry.get("link", ""),
                "published": published.isoformat() if published else "Unknown",
            })
    except Exception as e:
        logger.warning(f"Economic Times fetch failed: {e}")

    return articles


def fetch_all_news(stock: dict, lookback_hours: int = 24) -> list[dict]:
    """Aggregate news from all sources for a given stock."""
    all_articles = []

    all_articles += fetch_google_news_rss(stock["keywords"], lookback_hours)
    all_articles += fetch_moneycontrol_rss(stock["name"], lookback_hours)
    all_articles += fetch_economic_times_rss(stock["keywords"], lookback_hours)

    # Deduplicate by title similarity
    seen_titles = set()
    unique_articles = []
    for article in all_articles:
        title_key = article["title"][:60].lower().strip()
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique_articles.append(article)

    logger.info(f"  [{stock['ticker']}] Found {len(unique_articles)} unique articles")
    return unique_articles
