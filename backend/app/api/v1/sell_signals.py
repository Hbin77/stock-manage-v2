"""매도 신호 API 라우터"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database.connection import get_db
from app.database.models import SellSignal, Stock
from app.agents.orchestrator import OrchestratorAgent

router = APIRouter()
_orchestrator = OrchestratorAgent()


@router.get("/sell-signals", summary="현재 포트폴리오 매도 신호")
async def get_sell_signals():
    """
    포트폴리오 전체 매도 신호 즉시 분석 및 반환.
    기술적 분석 + 뉴스 감성 분석 후 신호 판단.
    매도 신호 발생 시 이메일 알림 발송.
    """
    result = await _orchestrator.analyze_portfolio_for_sells(force=True)

    signals = result.get("signals", [])
    if signals:
        try:
            from app.services.email_service import send_sell_signal_email
            send_sell_signal_email(signals)
        except Exception as e:
            from loguru import logger
            logger.error(f"이메일 발송 오류: {e}")

    return result


@router.post("/sell-signals/test-email", summary="이메일 알림 테스트 발송")
async def test_email_notification():
    """테스트용 샘플 매도 신호 이메일을 발송합니다."""
    from app.services.email_service import send_sell_signal_email
    from app.config.settings import settings

    if not all([settings.EMAIL_USER, settings.EMAIL_APP_PASSWORD, settings.NOTIFICATION_EMAIL]):
        return {
            "success": False,
            "message": "이메일 설정 미완료. .env 파일에 EMAIL_USER / EMAIL_APP_PASSWORD / NOTIFICATION_EMAIL을 설정하세요.",
        }

    test_signal = [{
        "ticker": "TEST",
        "name": "이메일 테스트 알림",
        "signal_type": "TAKE_PROFIT",
        "signal": "익절매",
        "pnl_pct": 3.5,
        "current_price": 105.00,
        "avg_buy_price": 100.00,
        "tech_score": 72.5,
        "news_sell_score": 25.0,
        "combined_score": 65.0,
        "is_scalp_trade": False,
        "reasoning": "이메일 알림 테스트 발송입니다. 실제 매도 신호가 아닙니다.",
        "tech_signals": ["테스트 신호 A", "테스트 신호 B"],
        "news_risk_factors": [],
        "news_reasoning": "테스트 목적 이메일",
    }]

    success = send_sell_signal_email(test_signal)
    if success:
        return {"success": True, "message": f"테스트 이메일 발송 완료 → {settings.NOTIFICATION_EMAIL}"}
    else:
        return {"success": False, "message": "이메일 발송 실패. 백엔드 로그를 확인하세요."}


@router.get("/sell-signals/history", summary="매도 신호 이력")
async def get_sell_signal_history(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """최근 매도 신호 이력 조회"""
    result = await db.execute(
        select(SellSignal, Stock)
        .join(Stock, SellSignal.stock_id == Stock.id)
        .order_by(desc(SellSignal.signal_at))
        .limit(limit)
    )
    signals = []
    for signal, stock in result.fetchall():
        signals.append({
            "id": signal.id,
            "ticker": stock.ticker,
            "name": stock.name,
            "signal_type": signal.signal_type,
            "signal": signal.signal,
            "combined_score": signal.combined_score,
            "pnl_pct": signal.pnl_pct,
            "reasoning": signal.reasoning,
            "signal_at": signal.signal_at.isoformat(),
            "is_acted_upon": signal.is_acted_upon,
        })
    return {"signals": signals, "count": len(signals)}
