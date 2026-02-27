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
    """테스트용 샘플 매도 신호 이메일을 발송합니다. 단계별 오류 메시지 포함."""
    import smtplib
    from app.config.settings import settings

    if not settings.EMAIL_USER:
        return {"success": False, "message": "EMAIL_USER 미설정. .env 파일을 확인하세요."}
    if not settings.EMAIL_APP_PASSWORD:
        return {"success": False, "message": "EMAIL_APP_PASSWORD 미설정. Gmail 앱 비밀번호(16자리)를 설정하세요."}
    if not settings.NOTIFICATION_EMAIL:
        return {"success": False, "message": "NOTIFICATION_EMAIL 미설정. 수신할 이메일 주소를 설정하세요."}

    # 1단계: SMTP 연결 및 인증 테스트 (상세 오류 반환)
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.EMAIL_USER, settings.EMAIL_APP_PASSWORD)
    except smtplib.SMTPAuthenticationError:
        return {
            "success": False,
            "message": (
                f"Gmail 인증 실패 ({settings.EMAIL_USER}). "
                "① Google 계정 → 보안 → 2단계 인증 활성화 확인 "
                "② 앱 비밀번호(16자리) 재생성 후 EMAIL_APP_PASSWORD 업데이트 필요"
            ),
        }
    except smtplib.SMTPConnectError as e:
        return {"success": False, "message": f"SMTP 서버 연결 실패: {e}"}
    except TimeoutError:
        return {"success": False, "message": "SMTP 연결 타임아웃. 네트워크 또는 방화벽을 확인하세요."}
    except Exception as e:
        return {"success": False, "message": f"연결 오류: {type(e).__name__}: {e}"}

    # 2단계: 테스트 이메일 발송
    from app.services.email_service import send_sell_signal_email

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
