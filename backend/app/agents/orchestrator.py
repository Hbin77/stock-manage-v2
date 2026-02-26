"""오케스트레이터 에이전트 - 멀티 에이전트 시스템 중앙 조율"""
from loguru import logger
from app.agents.technical_analyst import TechnicalAnalystAgent
from app.agents.news_analyst import NewsAnalystAgent
from app.agents.buy_recommender import BuyRecommenderAgent
from app.agents.portfolio_manager import PortfolioManagerAgent
from app.services.market_hours import is_market_open, get_market_status


class OrchestratorAgent:
    """
    멀티 에이전트 시스템의 중앙 조율자

    하위 에이전트:
    - TechnicalAnalystAgent: 기술적 분석 (RSI, MACD, BB, MA, Volume)
    - NewsAnalystAgent: 뉴스 감성 분석 (Claude AI)
    - BuyRecommenderAgent: S&P 500 스캔 → Top 3 매수 추천
    - PortfolioManagerAgent: 포트폴리오 관리 → 매도 신호 감지
    """

    def __init__(self):
        self.technical_analyst = TechnicalAnalystAgent()
        self.news_analyst = NewsAnalystAgent()
        self.buy_recommender = BuyRecommenderAgent()
        self.portfolio_manager = PortfolioManagerAgent()

    async def get_top3_recommendations(self) -> dict:
        """
        온디맨드 Top 3 매수 추천 생성
        NYSE 장중에만 실행 (또는 강제 실행 옵션)
        """
        market_status = get_market_status()
        logger.info(f"매수 추천 요청. 시장 상태: {market_status['message']}")

        try:
            top3 = await self.buy_recommender.get_top3()
            return {
                "success": True,
                "market_status": market_status,
                "recommendations": top3,
                "count": len(top3),
            }
        except Exception as e:
            logger.error(f"매수 추천 생성 실패: {e}")
            return {
                "success": False,
                "market_status": market_status,
                "recommendations": [],
                "count": 0,
                "error": str(e),
            }

    async def analyze_portfolio_for_sells(self, force: bool = False) -> dict:
        """
        포트폴리오 매도 신호 분석
        Celery에서 10분마다 호출 (NYSE 장중에만)
        force=True 시 장 마감 여부 무관하게 즉시 실행 (온디맨드 전용)
        """
        if not force and not is_market_open():
            market_status = get_market_status()
            logger.info(f"장 마감 시간. 매도 분석 건너뜀: {market_status['message']}")
            return {"skipped": True, "reason": market_status["message"], "signals": [], "hold_analysis": []}

        try:
            result = await self.portfolio_manager.check_sell_signals()
            sell_signals = result.get("sell_signals", [])
            hold_analysis = result.get("hold_analysis", [])
            return {
                "skipped": False,
                "signals": sell_signals,
                "count": len(sell_signals),
                "hold_analysis": hold_analysis,
            }
        except Exception as e:
            logger.error(f"포트폴리오 매도 분석 실패: {e}")
            return {"skipped": False, "signals": [], "count": 0, "hold_analysis": [], "error": str(e)}

    async def get_stock_analysis(self, ticker: str) -> dict:
        """단일 종목 전체 분석 (기술적 + 뉴스 + 베어리시 신호)"""
        from app.services.news_service import fetch_news
        from app.services.scoring import calculate_combined_score

        tech_result = await self.technical_analyst.analyze(ticker)
        headlines = await fetch_news(ticker)
        news_result = await self.news_analyst.analyze(ticker, headlines)

        tech_score = tech_result.get("tech_score", 50.0)
        news_score = news_result.get("news_score", 50.0)
        combined_score = calculate_combined_score(tech_score, news_score)

        return {
            "ticker": ticker,
            "tech_score": tech_score,
            "news_score": news_score,
            "combined_score": combined_score,
            "indicators": tech_result.get("indicators", {}),
            "bearish_signals": tech_result.get("bearish_signals", {}),
            "scalp_analysis": tech_result.get("scalp_analysis", {}),
            "news_analysis": news_result,
            "market_status": get_market_status(),
        }
