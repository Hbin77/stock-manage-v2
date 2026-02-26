"""추천 관련 Pydantic 스키마"""
from pydantic import BaseModel
from typing import Optional


class RecommendationItem(BaseModel):
    ticker: str
    tech_score: float
    news_score: float
    combined_score: float
    sentiment: str
    key_catalysts: list[str]
    reasoning: str
    signal: str


class MarketStatus(BaseModel):
    is_open: bool
    is_trading_day: bool
    current_time_est: str
    market_open: str
    market_close: str
    message: str


class RecommendationResponse(BaseModel):
    success: bool
    market_status: MarketStatus
    recommendations: list[RecommendationItem]
    count: int
    error: Optional[str] = None
