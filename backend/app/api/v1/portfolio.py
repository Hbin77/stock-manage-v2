"""포트폴리오 API 라우터"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.connection import get_db
from app.database.models import PortfolioHolding, Stock, Transaction
from app.schemas.portfolio import BuyRequest, HoldingResponse, SellSignalResponse
from app.services.market_data import fetch_current_price, fetch_ticker_info
from app.agents.orchestrator import OrchestratorAgent
from datetime import datetime
from loguru import logger

router = APIRouter()
_orchestrator = OrchestratorAgent()


@router.get("/portfolio", summary="포트폴리오 보유 현황")
async def get_portfolio(db: AsyncSession = Depends(get_db)):
    """현재 포트폴리오 보유 종목 목록 반환"""
    result = await db.execute(
        select(PortfolioHolding, Stock)
        .join(Stock, PortfolioHolding.stock_id == Stock.id)
    )
    holdings = []
    for holding, stock in result.fetchall():
        holdings.append({
            "id": holding.id,
            "ticker": stock.ticker,
            "name": stock.name,
            "sector": stock.sector,
            "quantity": holding.quantity,
            "avg_buy_price": holding.avg_buy_price,
            "total_invested": holding.total_invested,
            "current_price": holding.current_price,
            "unrealized_pnl": holding.unrealized_pnl,
            "unrealized_pnl_pct": holding.unrealized_pnl_pct,
            "first_bought_at": holding.first_bought_at.isoformat() if holding.first_bought_at else None,
            "last_updated_at": holding.last_updated_at.isoformat() if holding.last_updated_at else None,
            "is_scalp_trade": getattr(holding, "is_scalp_trade", False),
            "peak_price": getattr(holding, "peak_price", None),
            "trailing_stop_active": getattr(holding, "trailing_stop_active", False),
            "trailing_stop_price": getattr(holding, "trailing_stop_price", None),
            "breakeven_locked": getattr(holding, "breakeven_locked", False),
            "trading_days_held": getattr(holding, "trading_days_held", 0),
        })
    return {"holdings": holdings, "count": len(holdings)}


@router.post("/portfolio/buy", summary="종목 매수 추가")
async def buy_stock(request: BuyRequest, db: AsyncSession = Depends(get_db)):
    """포트폴리오에 종목 매수 추가"""
    ticker = request.ticker.upper()

    # 종목 조회 또는 생성
    result = await db.execute(select(Stock).where(Stock.ticker == ticker))
    stock = result.scalar_one_or_none()

    if not stock:
        info = await fetch_ticker_info(ticker)
        stock = Stock(
            ticker=ticker,
            name=info.get("name", ticker),
            sector=info.get("sector", ""),
            industry=info.get("industry", ""),
            market_cap=info.get("market_cap"),
        )
        db.add(stock)
        await db.flush()

    # 기존 보유 여부 확인
    result = await db.execute(
        select(PortfolioHolding).where(PortfolioHolding.stock_id == stock.id)
    )
    existing = result.scalar_one_or_none()

    total_amount = request.quantity * request.price

    if existing:
        # 평균 단가 재계산
        old_total = existing.avg_buy_price * existing.quantity
        new_total = old_total + total_amount
        new_qty = existing.quantity + request.quantity
        existing.avg_buy_price = new_total / new_qty
        existing.quantity = new_qty
        existing.total_invested += total_amount
    else:
        is_scalp = getattr(request, "strategy", "SCALP") == "SCALP"
        holding = PortfolioHolding(
            stock_id=stock.id,
            quantity=request.quantity,
            avg_buy_price=request.price,
            total_invested=total_amount,
            first_bought_at=datetime.utcnow(),
            is_scalp_trade=is_scalp,
            peak_price=request.price,
            trailing_stop_active=False,
            breakeven_locked=False,
            trading_days_held=0,
        )
        db.add(holding)

    # 거래 내역 기록
    transaction = Transaction(
        stock_id=stock.id,
        action="BUY",
        quantity=request.quantity,
        price=request.price,
        total_amount=total_amount,
        note=request.note,
        executed_at=datetime.utcnow(),
    )
    db.add(transaction)
    await db.commit()

    logger.info(f"매수 완료: {ticker} {request.quantity}주 @ ${request.price}")
    return {"success": True, "message": f"{ticker} {request.quantity}주 매수 완료", "ticker": ticker}


@router.delete("/portfolio/{ticker}", summary="종목 매도/삭제")
async def sell_stock(ticker: str, db: AsyncSession = Depends(get_db)):
    """포트폴리오에서 종목 매도 처리"""
    ticker = ticker.upper()

    result = await db.execute(
        select(PortfolioHolding, Stock)
        .join(Stock, PortfolioHolding.stock_id == Stock.id)
        .where(Stock.ticker == ticker)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail=f"{ticker}을 포트폴리오에서 찾을 수 없습니다.")

    holding, stock = row
    current_price = await fetch_current_price(ticker)
    sell_price = current_price or holding.avg_buy_price

    realized_pnl = (sell_price - holding.avg_buy_price) * holding.quantity

    # 거래 내역 기록
    transaction = Transaction(
        stock_id=stock.id,
        action="SELL",
        quantity=holding.quantity,
        price=sell_price,
        total_amount=sell_price * holding.quantity,
        realized_pnl=realized_pnl,
        executed_at=datetime.utcnow(),
    )
    db.add(transaction)

    await db.delete(holding)
    await db.commit()

    logger.info(f"매도 완료: {ticker} 실현손익 ${realized_pnl:.2f}")
    return {
        "success": True,
        "message": f"{ticker} 매도 완료",
        "realized_pnl": round(realized_pnl, 2),
        "sell_price": sell_price,
    }


@router.get("/portfolio/transactions", summary="거래 내역 조회")
async def get_transactions(db: AsyncSession = Depends(get_db)):
    """전체 거래 내역 반환"""
    result = await db.execute(
        select(Transaction, Stock)
        .join(Stock, Transaction.stock_id == Stock.id)
        .order_by(Transaction.executed_at.desc())
    )
    transactions = []
    for tx, stock in result.fetchall():
        transactions.append({
            "id": tx.id,
            "ticker": stock.ticker,
            "name": stock.name,
            "action": tx.action,
            "quantity": tx.quantity,
            "price": tx.price,
            "total_amount": tx.total_amount,
            "realized_pnl": tx.realized_pnl,
            "note": tx.note,
            "executed_at": tx.executed_at.isoformat(),
        })
    return {"transactions": transactions, "count": len(transactions)}
