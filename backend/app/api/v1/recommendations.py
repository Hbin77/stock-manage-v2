"""매수 추천 API 라우터"""
from fastapi import APIRouter, HTTPException
from app.agents.orchestrator import OrchestratorAgent
from app.schemas.recommendation import RecommendationResponse

router = APIRouter()
_orchestrator = OrchestratorAgent()


@router.get("/recommendations", response_model=RecommendationResponse, summary="Top 3 매수 추천")
async def get_recommendations():
    """
    S&P 500 전체 스캔 후 통합 점수 상위 3개 매수 추천 종목 반환.
    
    기술적 분석(60%) + 뉴스 감성 분석(40%) 기반 점수 계산.
    분석에 수 분이 소요될 수 있습니다.
    """
    result = await _orchestrator.get_top3_recommendations()
    if not result["success"] and result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    return result
