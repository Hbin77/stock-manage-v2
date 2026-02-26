"""포트폴리오 관련 Pydantic 스키마"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class BuyRequest(BaseModel):
    ticker: str
    quantity: float
    price: float
    note: Optional[str] = None
    strategy: str = "SCALP"  # "SCALP" 또는 "SWING"


class HoldingResponse(BaseModel):
    id: int
    ticker: str
    name: str
    quantity: float
    avg_buy_price: float
    total_invested: float
    current_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    unrealized_pnl_pct: Optional[float] = None
    first_bought_at: Optional[str] = None


class SellSignalResponse(BaseModel):
    ticker: str
    name: str
    signal_type: str
    signal: str
    combined_score: float
    tech_score: float
    news_score: float
    pnl_pct: Optional[float] = None
    current_price: Optional[float] = None
    avg_buy_price: float
    reasoning: str
