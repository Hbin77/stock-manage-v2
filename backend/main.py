"""FastAPI 애플리케이션 진입점 - 주식 추천 및 포트폴리오 관리 시스템"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.database.connection import init_db
from app.api.v1 import recommendations, portfolio, sell_signals, scores, sse
from app.services.market_hours import get_market_status


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 이벤트 처리"""
    logger.info("주식 추천 시스템 시작...")
    await init_db()
    market = get_market_status()
    logger.info(f"시장 상태: {market['message']} ({market['current_time_est']})")
    yield
    logger.info("주식 추천 시스템 종료")


app = FastAPI(
    title="주식 추천 및 포트폴리오 관리 시스템",
    description="""
## 멀티 에이전트 기반 S&P 500 주식 분석 API

### 주요 기능
- **Top 3 매수 추천**: S&P 500 전체 스캔 후 기술적 분석 + 뉴스 분석 통합 점수 상위 3개 반환
- **포트폴리오 관리**: 보유 종목 추가/조회/매도
- **매도 신호**: 10분 주기로 포트폴리오 자동 분석 (NYSE 장중)
- **실시간 알림**: SSE 기반 실시간 매도 신호 수신

### 점수 계산
- 기술적 점수 (60%): RSI, MACD, 볼린저밴드, 이동평균, 거래량
- 뉴스 점수 (40%): Claude AI 뉴스 감성 분석
- 매수 임계값: 70점 이상
- 매도 임계값: 40점 미만
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 설정 (개인 NAS 도구 - 모든 origin 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(recommendations.router, prefix="/api/v1", tags=["추천"])
app.include_router(portfolio.router, prefix="/api/v1", tags=["포트폴리오"])
app.include_router(sell_signals.router, prefix="/api/v1", tags=["매도신호"])
app.include_router(scores.router, prefix="/api/v1", tags=["점수"])
app.include_router(sse.router, prefix="/api/v1", tags=["실시간"])


@app.get("/", summary="루트")
async def root():
    return {
        "message": "주식 추천 및 포트폴리오 관리 시스템 API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", summary="헬스체크")
async def health():
    """서비스 상태 및 시장 정보 반환"""
    market = get_market_status()
    return {
        "status": "ok",
        "market": market,
    }
