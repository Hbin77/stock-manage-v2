"""S&P 500 매수 추천 에이전트"""
import asyncio
from loguru import logger
from app.config.sp500_tickers import SP500_TICKERS
from app.agents.technical_analyst import TechnicalAnalystAgent
from app.agents.news_analyst import NewsAnalystAgent
from app.services.news_service import fetch_news
from app.services.scoring import calculate_combined_score
from app.config.settings import settings
from app.services.technical_indicators import calculate_scalp_entry_score


async def _get_portfolio_tickers() -> set[str]:
    """현재 포트폴리오 보유 종목 티커 조회"""
    try:
        from sqlalchemy import select
        from app.database.connection import AsyncSessionLocal
        from app.database.models import PortfolioHolding, Stock

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Stock.ticker)
                .join(PortfolioHolding, PortfolioHolding.stock_id == Stock.id)
            )
            return {row[0] for row in result.fetchall()}
    except Exception as e:
        logger.error(f"포트폴리오 티커 조회 실패: {e}")
        return set()


async def _validate_scalp_entry(ticker: str) -> dict:
    """단타 진입 조건 검증 (최근 65거래일 데이터 사용)"""
    try:
        from app.services.market_data import fetch_ohlcv
        df = await fetch_ohlcv(ticker, period="1y")
        if df is None or df.empty or len(df) < 55:
            return {"all_conditions_pass": False, "entry_score": 0.0, "validation": {}}
        df_3mo = df.iloc[-65:]
        return calculate_scalp_entry_score(df_3mo)
    except Exception as e:
        logger.error(f"{ticker} 단타 진입 검증 실패: {e}")
        return {"all_conditions_pass": False, "entry_score": 0.0, "validation": {}}


class BuyRecommenderAgent:
    """S&P 500 전체 스캔 후 Top 3 매수 추천 에이전트"""

    def __init__(self):
        self.technical_analyst = TechnicalAnalystAgent()
        self.news_analyst = NewsAnalystAgent()

    async def get_top3(self) -> list[dict]:
        """
        S&P 500 전체 스캔 → Top 3 매수 추천 (이미 보유 중인 종목 제외)

        1단계: 포트폴리오 보유 종목 조회 후 제외
        2단계: 기술적 분석으로 전체 스캔 (연속 스케일 점수)
        3단계: 상위 20개만 뉴스 분석 (Claude API 비용 최적화)
        4단계: 통합 점수 계산 및 상위 3개 반환
               - 뉴스 분석 가능: BUY_THRESHOLD(70) 적용
               - 뉴스 분석 불가: FALLBACK_BUY_THRESHOLD(62) 적용
        """
        # 1단계: 포트폴리오 보유 종목 제외
        portfolio_tickers = await _get_portfolio_tickers()
        scan_tickers = [t for t in SP500_TICKERS if t not in portfolio_tickers]

        if portfolio_tickers:
            logger.info(f"포트폴리오 보유 종목 제외: {sorted(portfolio_tickers)} → {len(scan_tickers)}개 스캔")
        logger.info(f"S&P 500 {len(scan_tickers)}개 종목 매수 추천 분석 시작")

        # 2단계: 기술적 점수 전체 계산
        logger.info("기술적 분석 중...")
        tech_scores = await self.technical_analyst.score_batch(scan_tickers, max_concurrent=30)

        if not tech_scores:
            logger.error("기술적 분석 실패")
            return []

        # 상위 20개 필터링
        top20 = sorted(tech_scores.items(), key=lambda x: x[1], reverse=True)[:20]
        logger.info(f"기술적 분석 완료. 상위 20개: {[t for t, s in top20[:5]]} (최고 {top20[0][1]:.1f}점)")

        # 3단계: 상위 20개 뉴스 수집 및 분석
        news_tasks = [fetch_news(ticker) for ticker, _ in top20]
        all_headlines = await asyncio.gather(*news_tasks, return_exceptions=True)

        ticker_headlines = {}
        for (ticker, _), headlines in zip(top20, all_headlines):
            ticker_headlines[ticker] = headlines if not isinstance(headlines, Exception) else []

        news_results = await self.news_analyst.analyze_batch(ticker_headlines, max_concurrent=5)

        # 단타 진입 조건 병렬 검증 (상위 20개 종목)
        scalp_tasks = [_validate_scalp_entry(ticker) for ticker, _ in top20]
        scalp_results_raw = await asyncio.gather(*scalp_tasks, return_exceptions=True)
        scalp_results = {
            ticker: (sr if not isinstance(sr, Exception) else {"all_conditions_pass": False, "entry_score": 0.0})
            for (ticker, _), sr in zip(top20, scalp_results_raw)
        }

        # 통합 점수 계산 + 단타 조건 필터 + 임계값 적용
        candidates = []
        for ticker, tech_score in top20:
            news_data = news_results.get(ticker, {"news_score": 50.0, "reasoning": "", "news_available": False})
            news_score = news_data.get("news_score", 50.0)
            news_available = news_data.get("news_available", False)
            combined_score = calculate_combined_score(tech_score, news_score)

            scalp_data = scalp_results.get(ticker, {"all_conditions_pass": False, "entry_score": 0.0})
            scalp_ok = scalp_data.get("all_conditions_pass", False)
            entry_score = scalp_data.get("entry_score", 0.0)
            scalp_validation = scalp_data.get("validation", {})

            # 단타 매수: combined_score >= 75 AND 모든 모멘텀 조건 충족
            # 일반 매수: combined_score >= 70 (폴백)
            if scalp_ok and combined_score >= settings.SCALP_BUY_THRESHOLD:
                signal = "단타 매수 추천"
                strategy = "SCALP"
            elif combined_score >= (settings.BUY_THRESHOLD if news_available else settings.FALLBACK_BUY_THRESHOLD):
                signal = "매수 추천"
                strategy = "SWING"
            else:
                signal = "관망"
                strategy = "SWING"

            effective_threshold = settings.SCALP_BUY_THRESHOLD if scalp_ok else (
                settings.BUY_THRESHOLD if news_available else settings.FALLBACK_BUY_THRESHOLD
            )

            candidates.append({
                "ticker": ticker,
                "tech_score": round(tech_score, 2),
                "news_score": round(news_score, 2),
                "combined_score": combined_score,
                "entry_score": round(entry_score, 2),
                "scalp_conditions_pass": scalp_ok,
                "scalp_validation": scalp_validation,
                "sentiment": news_data.get("sentiment", "중립"),
                "key_catalysts": news_data.get("key_catalysts", []),
                "reasoning": news_data.get("reasoning", ""),
                "news_available": news_available,
                "signal": signal,
                "strategy": strategy,
                "threshold_used": f"{'단타' if scalp_ok else ('정상' if news_available else '폴백')}({effective_threshold}점)",
            })

        # 단타 추천 우선, 없으면 일반 매수 추천, 통합점수 기준 상위 3개
        top3 = sorted(
            candidates,
            key=lambda x: (x["strategy"] == "SCALP", x["combined_score"]),
            reverse=True
        )[:3]
        buy_count = sum(1 for c in top3 if c["signal"] in ("단타 매수 추천", "매수 추천"))
        scalp_count = sum(1 for c in top3 if c["strategy"] == "SCALP")
        logger.info(f"Top 3 매수 추천 완료: {[c['ticker'] for c in top3]} | 매수신호: {buy_count}개 (단타: {scalp_count}개)")

        return top3
