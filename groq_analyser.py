"""
groq_analyser.py
Sends news to Groq (free tier) for equity research style analysis.
Model: llama3-70b-8192 (free, fast)
"""

import os
import json
import logging
from groq import Groq

logger = logging.getLogger(__name__)

client = None

def get_client():
    global client
    if client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")
        client = Groq(api_key=api_key)
    return client


ANALYSIS_PROMPT = """You are a seasoned Indian equity research analyst covering NSE/BSE listed stocks.

Company: {company_name} ({ticker})
Exchange: {exchange}

Below are news articles/updates from the last 24 hours. Analyse them and provide a structured report.

NEWS ITEMS:
{news_text}

Provide your analysis in the following JSON format ONLY (no markdown, no extra text):
{{
  "overall_sentiment": "BULLISH | BEARISH | NEUTRAL | NO_NEWS",
  "sentiment_strength": "STRONG | MODERATE | MILD",
  "key_events": [
    {{"event": "brief description", "impact": "POSITIVE | NEGATIVE | NEUTRAL", "importance": "HIGH | MEDIUM | LOW"}}
  ],
  "stock_impact_summary": "2-3 sentence plain English summary of what happened and likely near-term impact on stock price",
  "what_to_watch": ["item1", "item2"],
  "analyst_note": "One sharp insight that a retail investor might miss",
  "news_count": {news_count}
}}

If there is no relevant news, set overall_sentiment to NO_NEWS and leave other fields minimal.
"""


NO_NEWS_TEMPLATE = {
    "overall_sentiment": "NO_NEWS",
    "sentiment_strength": "N/A",
    "key_events": [],
    "stock_impact_summary": "No significant news found in the last 24 hours.",
    "what_to_watch": ["Monitor for any exchange filings", "Check for sector-level news"],
    "analyst_note": "Quiet days can precede significant moves — watch volumes.",
    "news_count": 0,
}


def analyse_stock(stock: dict, articles: list[dict], model: str = "llama3-70b-8192") -> dict:
    """Send news articles to Groq and get structured analysis back."""

    if not articles:
        logger.info(f"  [{stock['ticker']}] No news — skipping LLM call")
        result = NO_NEWS_TEMPLATE.copy()
        result["ticker"] = stock["ticker"]
        result["company_name"] = stock["name"]
        return result

    # Format news for the prompt
    news_lines = []
    for i, a in enumerate(articles[:8], 1):  # Max 8 articles per stock
        news_lines.append(
            f"[{i}] SOURCE: {a['source']} | DATE: {a['published']}\n"
            f"    TITLE: {a['title']}\n"
            f"    SUMMARY: {a['summary'][:300]}\n"
        )
    news_text = "\n".join(news_lines)

    prompt = ANALYSIS_PROMPT.format(
        company_name=stock["name"],
        ticker=stock["ticker"],
        exchange=stock["exchange"],
        news_text=news_text,
        news_count=len(articles),
    )

    try:
        response = get_client().chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=800,
        )
        raw = response.choices[0].message.content.strip()

        # Clean up any accidental markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        analysis = json.loads(raw)
        analysis["ticker"] = stock["ticker"]
        analysis["company_name"] = stock["name"]
        logger.info(f"  [{stock['ticker']}] Analysis: {analysis['overall_sentiment']} ({analysis['sentiment_strength']})")
        return analysis

    except json.JSONDecodeError as e:
        logger.error(f"  [{stock['ticker']}] JSON parse error: {e}")
        return {**NO_NEWS_TEMPLATE, "ticker": stock["ticker"], "company_name": stock["name"],
                "analyst_note": "Analysis parsing failed — raw LLM output malformed."}
    except Exception as e:
        logger.error(f"  [{stock['ticker']}] Groq API error: {e}")
        return {**NO_NEWS_TEMPLATE, "ticker": stock["ticker"], "company_name": stock["name"],
                "analyst_note": f"LLM call failed: {str(e)[:100]}"}
