"""점수 관련 Pydantic 스키마"""
from pydantic import BaseModel
from typing import Optional


class IndicatorData(BaseModel):
    rsi_14: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    ma_20: Optional[float] = None
    ma_50: Optional[float] = None
    ma_200: Optional[float] = None
    volume_ma_20: Optional[float] = None


class StockScoreResponse(BaseModel):
    ticker: str
    tech_score: float
    news_score: float
    combined_score: float
    indicators: IndicatorData
    news_analysis: Optional[dict] = None
    market_status: Optional[dict] = None
