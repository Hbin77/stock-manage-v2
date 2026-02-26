from datetime import datetime
from typing import Optional
import datetime as dt
from sqlalchemy import (
    Integer, String, Float, BigInteger, Boolean, Text,
    DateTime, Date, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.connection import Base


class Stock(Base):
    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    sector: Mapped[Optional[str]] = mapped_column(String(100))
    industry: Mapped[Optional[str]] = mapped_column(String(100))
    market_cap: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    price_history: Mapped[list["PriceHistory"]] = relationship(back_populates="stock", cascade="all, delete-orphan")
    scores: Mapped[list["StockScore"]] = relationship(back_populates="stock", cascade="all, delete-orphan")
    news_sentiments: Mapped[list["NewsSentiment"]] = relationship(back_populates="stock", cascade="all, delete-orphan")
    holding: Mapped[Optional["PortfolioHolding"]] = relationship(back_populates="stock", uselist=False)
    sell_signals: Mapped[list["SellSignal"]] = relationship(back_populates="stock", cascade="all, delete-orphan")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="stock", cascade="all, delete-orphan")


class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"))
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[int] = mapped_column(BigInteger)
    adj_close: Mapped[Optional[float]] = mapped_column(Float)

    stock: Mapped["Stock"] = relationship(back_populates="price_history")

    __table_args__ = (
        UniqueConstraint("stock_id", "timestamp"),
        Index("idx_price_stock_ts", "stock_id", "timestamp"),
    )


class TechnicalIndicator(Base):
    __tablename__ = "technical_indicators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"))
    trade_date: Mapped[dt.date] = mapped_column(Date)
    rsi_14: Mapped[Optional[float]] = mapped_column(Float)
    macd: Mapped[Optional[float]] = mapped_column(Float)
    macd_signal: Mapped[Optional[float]] = mapped_column(Float)
    macd_hist: Mapped[Optional[float]] = mapped_column(Float)
    bb_upper: Mapped[Optional[float]] = mapped_column(Float)
    bb_middle: Mapped[Optional[float]] = mapped_column(Float)
    bb_lower: Mapped[Optional[float]] = mapped_column(Float)
    ma_20: Mapped[Optional[float]] = mapped_column(Float)
    ma_50: Mapped[Optional[float]] = mapped_column(Float)
    ma_200: Mapped[Optional[float]] = mapped_column(Float)
    volume_ma_20: Mapped[Optional[float]] = mapped_column(Float)
    tech_score: Mapped[Optional[float]] = mapped_column(Float)

    __table_args__ = (
        UniqueConstraint("stock_id", "trade_date"),
    )


class NewsSentiment(Base):
    __tablename__ = "news_sentiment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"))
    fetched_date: Mapped[dt.date] = mapped_column(Date)
    news_score: Mapped[Optional[float]] = mapped_column(Float)
    headline_count: Mapped[Optional[int]] = mapped_column(Integer)
    headlines_json: Mapped[Optional[str]] = mapped_column(Text)
    reasoning: Mapped[Optional[str]] = mapped_column(Text)

    stock: Mapped["Stock"] = relationship(back_populates="news_sentiments")

    __table_args__ = (
        UniqueConstraint("stock_id", "fetched_date"),
    )


class StockScore(Base):
    __tablename__ = "stock_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"))
    scored_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    tech_score: Mapped[float] = mapped_column(Float)
    news_score: Mapped[float] = mapped_column(Float)
    combined_score: Mapped[float] = mapped_column(Float)
    rank_in_sp500: Mapped[Optional[int]] = mapped_column(Integer)

    stock: Mapped["Stock"] = relationship(back_populates="scores")

    __table_args__ = (
        Index("idx_scores_combined", "combined_score"),
    )


class PortfolioHolding(Base):
    __tablename__ = "portfolio_holdings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), unique=True)
    quantity: Mapped[float] = mapped_column(Float)
    avg_buy_price: Mapped[float] = mapped_column(Float)
    total_invested: Mapped[float] = mapped_column(Float)
    current_price: Mapped[Optional[float]] = mapped_column(Float)
    unrealized_pnl: Mapped[Optional[float]] = mapped_column(Float)
    unrealized_pnl_pct: Mapped[Optional[float]] = mapped_column(Float)
    first_bought_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 단타 전략 필드
    is_scalp_trade: Mapped[bool] = mapped_column(Boolean, default=False)
    peak_price: Mapped[Optional[float]] = mapped_column(Float)
    trailing_stop_active: Mapped[bool] = mapped_column(Boolean, default=False)
    trailing_stop_price: Mapped[Optional[float]] = mapped_column(Float)
    breakeven_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    trading_days_held: Mapped[int] = mapped_column(Integer, default=0)

    stock: Mapped["Stock"] = relationship(back_populates="holding")


class SellSignal(Base):
    __tablename__ = "sell_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"))
    signal_type: Mapped[str] = mapped_column(String(20))
    signal: Mapped[str] = mapped_column(String(15))
    combined_score: Mapped[Optional[float]] = mapped_column(Float)
    pnl_pct: Mapped[Optional[float]] = mapped_column(Float)
    reasoning: Mapped[Optional[str]] = mapped_column(Text)
    signal_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_acted_upon: Mapped[bool] = mapped_column(Boolean, default=False)

    stock: Mapped["Stock"] = relationship(back_populates="sell_signals")

    __table_args__ = (
        Index("idx_sell_signals_stock", "stock_id", "signal_at"),
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"))
    action: Mapped[str] = mapped_column(String(4))
    quantity: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    total_amount: Mapped[float] = mapped_column(Float)
    realized_pnl: Mapped[Optional[float]] = mapped_column(Float)
    note: Mapped[Optional[str]] = mapped_column(Text)
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    stock: Mapped["Stock"] = relationship(back_populates="transactions")
