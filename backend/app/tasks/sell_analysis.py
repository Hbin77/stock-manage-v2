"""Celery 태스크: 10분마다 포트폴리오 매도 분석"""
import asyncio
import json
from loguru import logger
from app.tasks.celery_app import celery_app
from app.services.market_hours import is_market_open


@celery_app.task(name="app.tasks.sell_analysis.run_sell_analysis", bind=True, max_retries=2)
def run_sell_analysis(self):
    """
    NYSE 장중에만 실행 (9:30 AM - 4:00 PM EST)
    10분 주기로 포트폴리오 매도 신호 분석
    """
    if not is_market_open():
        logger.info("장 마감 시간. 매도 분석 건너뜀.")
        return {"status": "skipped", "reason": "장 마감 시간"}

    try:
        from app.agents.orchestrator import OrchestratorAgent
        orchestrator = OrchestratorAgent()
        result = asyncio.run(orchestrator.analyze_portfolio_for_sells())

        signals = result.get("signals", [])
        logger.info(f"매도 분석 완료: {len(signals)}개 신호")

        # Redis Pub/Sub + 이메일 알림
        if signals:
            _publish_sell_signals(signals)
            _send_email_notification(signals)

        return {
            "status": "completed",
            "signals_count": len(signals),
            "signals": signals,
        }

    except Exception as exc:
        logger.error(f"매도 분석 태스크 오류: {exc}")
        raise self.retry(exc=exc, countdown=60)


def _send_email_notification(signals: list[dict]):
    """매도 신호 이메일 발송"""
    try:
        from app.services.email_service import send_sell_signal_email
        send_sell_signal_email(signals)
    except Exception as e:
        logger.error(f"이메일 발송 오류: {e}")


def _publish_sell_signals(signals: list[dict]):
    """Redis Pub/Sub으로 매도 신호 발행"""
    try:
        import redis
        from app.config.settings import settings

        r = redis.from_url(settings.REDIS_URL)
        event = json.dumps({
            "type": "sell_signals",
            "data": signals,
        })
        r.publish("stock_events", event)
        logger.info(f"매도 신호 {len(signals)}개 Pub/Sub 발행 완료")
    except Exception as e:
        logger.error(f"Redis Pub/Sub 발행 실패: {e}")
