"""yfinance 기반 주식 시장 데이터 수집 서비스"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
import pandas as pd
import yfinance as yf
from loguru import logger

_executor = ThreadPoolExecutor(max_workers=30)  # async semaphore(30)와 일치


def _fetch_ticker_data(ticker: str, period: str = "6mo", interval: str = "1d") -> Optional[pd.DataFrame]:
    """동기 yfinance 데이터 수집 (ThreadPool에서 실행)"""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)
        if df.empty:
            logger.warning(f"{ticker}: 데이터 없음")
            return None
        df.columns = [c.lower() for c in df.columns]
        df.index = pd.to_datetime(df.index)
        return df
    except Exception as e:
        logger.error(f"{ticker} 데이터 수집 실패: {e}")
        return None


def _fetch_current_price(ticker: str) -> Optional[float]:
    """현재가 조회"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.fast_info
        return float(info.last_price) if info.last_price else None
    except Exception as e:
        logger.error(f"{ticker} 현재가 조회 실패: {e}")
        return None


def _fetch_ticker_info(ticker: str) -> dict:
    """종목 기본 정보 조회"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            "name": info.get("longName", info.get("shortName", ticker)),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "market_cap": info.get("marketCap", None),
        }
    except Exception as e:
        logger.error(f"{ticker} 정보 조회 실패: {e}")
        return {"name": ticker, "sector": "", "industry": "", "market_cap": None}


async def fetch_ohlcv(ticker: str, period: str = "6mo") -> Optional[pd.DataFrame]:
    """비동기 OHLCV 데이터 수집"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _fetch_ticker_data, ticker, period)


async def fetch_current_price(ticker: str) -> Optional[float]:
    """비동기 현재가 조회"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _fetch_current_price, ticker)


async def fetch_ticker_info(ticker: str) -> dict:
    """비동기 종목 정보 조회"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _fetch_ticker_info, ticker)


async def fetch_multiple_prices(tickers: list[str]) -> dict[str, Optional[float]]:
    """여러 종목 현재가 동시 조회"""
    tasks = [fetch_current_price(ticker) for ticker in tickers]
    prices = await asyncio.gather(*tasks, return_exceptions=True)
    return {
        ticker: price if not isinstance(price, Exception) else None
        for ticker, price in zip(tickers, prices)
    }
