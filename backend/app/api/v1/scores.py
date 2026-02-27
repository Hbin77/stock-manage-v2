"""종목 점수 API 라우터"""
from fastapi import APIRouter, HTTPException
from app.agents.orchestrator import OrchestratorAgent
from app.schemas.score import StockScoreResponse
from app.config.sp500_tickers import SP500_TICKERS, TICKER_EXTRA_GROUPS

router = APIRouter()
_orchestrator = OrchestratorAgent()


@router.get("/scores/{ticker}", summary="종목 점수 조회")
async def get_stock_score(ticker: str):
    """
    특정 종목의 기술적 분석 + 뉴스 감성 분석 + 통합 점수 반환.
    """
    ticker = ticker.upper()
    try:
        result = await _orchestrator.get_stock_analysis(ticker)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{ticker} 분석 실패: {str(e)}")


@router.get("/tickers", summary="분석 대상 종목 목록")
async def get_tickers():
    """분석 대상 전체 티커 목록 및 카테고리별 추가 종목 반환"""
    extra_set = {t for group in TICKER_EXTRA_GROUPS.values() for t in group}
    sp500_base = [t for t in SP500_TICKERS if t not in extra_set]
    return {
        "total": len(SP500_TICKERS),
        "sp500_count": len(sp500_base),
        "extra_count": len(extra_set),
        "sp500_tickers": sp500_base,
        "extra_groups": TICKER_EXTRA_GROUPS,
    }


@router.get("/market-status", summary="시장 상태 조회")
async def get_market_status():
    """NYSE 현재 장 운영 상태 반환"""
    from app.services.market_hours import get_market_status
    return get_market_status()
