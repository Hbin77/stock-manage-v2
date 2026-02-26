"""기술적 분석 에이전트"""
import asyncio
from typing import Optional
import pandas as pd
from loguru import logger
from app.services.market_data import fetch_ohlcv
from app.services.technical_indicators import calculate_tech_score, calculate_all_indicators, detect_bearish_signals, calculate_scalp_entry_score


class TechnicalAnalystAgent:
    """기술적 지표 기반 종목 점수 계산 에이전트"""

    async def analyze(self, ticker: str) -> dict:
        """단일 종목 기술적 분석 (1년 데이터 + 3개월 단타 분석)"""
        try:
            df = await fetch_ohlcv(ticker, period="1y")
            if df is None or df.empty:
                return {"ticker": ticker, "tech_score": 50.0, "indicators": {}, "bearish_signals": {}, "scalp_analysis": {}, "error": "데이터 없음"}

            indicators = calculate_all_indicators(df)
            tech_score = indicators.get("tech_score", 50.0)
            bearish = detect_bearish_signals(df)

            # 단타 분석: 최근 3개월 데이터 사용
            df_3mo = df.iloc[-65:] if len(df) >= 65 else df  # 약 3개월 = 65 거래일
            scalp = calculate_scalp_entry_score(df_3mo)

            return {
                "ticker": ticker,
                "tech_score": tech_score,
                "indicators": indicators,
                "bearish_signals": bearish,
                "scalp_analysis": scalp,
                "error": None,
            }
        except Exception as e:
            logger.error(f"{ticker} 기술적 분석 실패: {e}")
            return {"ticker": ticker, "tech_score": 50.0, "indicators": {}, "bearish_signals": {}, "scalp_analysis": {}, "error": str(e)}

    async def score_batch(self, tickers: list[str], max_concurrent: int = 20) -> dict[str, float]:
        """여러 종목 기술적 점수 일괄 계산 (동시 처리)"""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def analyze_with_semaphore(ticker: str) -> tuple[str, float]:
            async with semaphore:
                result = await self.analyze(ticker)
                return ticker, result["tech_score"]

        tasks = [analyze_with_semaphore(ticker) for ticker in tickers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        scores = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"배치 분석 오류: {result}")
                continue
            ticker, score = result
            scores[ticker] = score

        return scores
