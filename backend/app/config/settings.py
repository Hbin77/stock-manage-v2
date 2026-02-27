from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Anthropic Claude
    ANTHROPIC_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-sonnet-4-6"

    # PostgreSQL
    DATABASE_URL: str = "postgresql+asyncpg://stock:password@postgres:5432/stockdb"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # 뉴스 API
    NEWS_API_KEY: str = ""

    # 점수 임계값
    BUY_THRESHOLD: float = 70.0
    # 뉴스 분석 불가 시 폴백 임계값 (tech 점수 ≥ 66.7 이면 통과)
    # 계산: 0.6*tech + 0.4*50 ≥ 62 → tech ≥ 66.7
    FALLBACK_BUY_THRESHOLD: float = 62.0
    SELL_THRESHOLD: float = 40.0
    STOP_LOSS_PCT: float = -5.0
    TAKE_PROFIT_PCT: float = 15.0

    # 가중치
    TECH_WEIGHT: float = 0.6
    NEWS_WEIGHT: float = 0.4

    # 거래 시간 (EST)
    MARKET_OPEN: str = "09:30"
    MARKET_CLOSE: str = "16:00"

    # ─── 단타 전략 파라미터 ───────────────────────────────────────────
    # 손절: -2%, 익절: +3%, 손실리스크 최소화로 일관 수익 추구
    SCALP_STOP_LOSS_PCT: float = -2.0         # 기본 손절 -2%
    SCALP_TAKE_PROFIT_PCT: float = 3.0        # 기본 익절 +3%
    SCALP_BREAKEVEN_TRIGGER_PCT: float = 1.5  # +1.5% 달성 시 손절→매수가 이동
    SCALP_TRAIL_TRIGGER_PCT: float = 2.0      # +2% 달성 시 트레일링 스톱 시작
    SCALP_TRAIL_PCT: float = 1.0              # 트레일: 고점 대비 -1% 유지
    SCALP_MAX_HOLDING_DAYS: int = 5           # 최대 보유 거래일 (타임스톱)
    SCALP_BUY_THRESHOLD: float = 75.0         # 단타 매수 임계값 (기존 70→75)
    SCALP_RSI_MIN: float = 45.0               # RSI 허용 최솟값
    SCALP_RSI_MAX: float = 68.0               # RSI 허용 최댓값
    SCALP_VOLUME_MULTIPLIER: float = 1.3      # 거래량 확인 배율

    # ─── 스윙 매도 신호 임계값 ────────────────────────────────────────
    SWING_NEWS_COMBINED_THRESHOLD: float = 60.0   # HIGH 신호 + 뉴스 sell_score 이상 시 매도 (55→60, 노이즈 감소)
    SWING_NEWS_ALONE_THRESHOLD: float = 70.0      # 뉴스 단독 매도 sell_score 기준

    # 이메일 알림
    EMAIL_USER: str = ""
    EMAIL_APP_PASSWORD: str = ""
    NOTIFICATION_EMAIL: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
