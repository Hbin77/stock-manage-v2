"""뉴스 수집 서비스 (NewsAPI.org)"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Optional
import requests
from loguru import logger
from app.config.settings import settings

_executor = ThreadPoolExecutor(max_workers=5)


def _fetch_news_sync(ticker: str, company_name: str = "") -> list[str]:
    """동기 뉴스 수집"""
    headlines = []

    if not settings.NEWS_API_KEY:
        logger.warning("NEWS_API_KEY가 설정되지 않았습니다. 뉴스 분석을 건너뜁니다.")
        return headlines

    try:
        query = f"{ticker} OR {company_name}" if company_name else ticker
        from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "from": from_date,
            "sortBy": "relevancy",
            "language": "en",
            "pageSize": 10,
            "apiKey": settings.NEWS_API_KEY,
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        articles = data.get("articles", [])

        for article in articles:
            title = article.get("title", "")
            description = article.get("description", "")
            if title and title != "[Removed]":
                text = f"{title}. {description}" if description else title
                headlines.append(text[:200])

    except Exception as e:
        logger.error(f"{ticker} 뉴스 수집 실패: {e}")

    return headlines


async def fetch_news(ticker: str, company_name: str = "") -> list[str]:
    """비동기 뉴스 수집"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _fetch_news_sync, ticker, company_name)
