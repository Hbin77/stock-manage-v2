"""통합 점수 계산 서비스"""
from loguru import logger
from app.config.settings import settings


def calculate_combined_score(tech_score: float, news_score: float) -> float:
    """
    통합 점수 계산
    combined_score = TECH_WEIGHT * tech_score + NEWS_WEIGHT * news_score
    기본값: 0.6 * tech + 0.4 * news
    """
    combined = settings.TECH_WEIGHT * tech_score + settings.NEWS_WEIGHT * news_score
    return round(min(100.0, max(0.0, combined)), 2)


def get_signal(combined_score: float, pnl_pct: float = 0.0) -> dict:
    """
    신호 판단
    - 매수: combined_score > BUY_THRESHOLD (70)
    - 매도: combined_score < SELL_THRESHOLD (40)
    - 손절: pnl_pct < STOP_LOSS_PCT (-5%)
    - 익절: pnl_pct > TAKE_PROFIT_PCT (15%)
    """
    signals = []

    # 손절/익절 신호 먼저 체크 (P&L 조건이 점수 신호보다 우선)
    if pnl_pct != 0.0:
        if pnl_pct <= settings.STOP_LOSS_PCT:
            signals.append({
                "type": "STOP_LOSS",
                "signal": "손절매",
                "reason": f"손실률 {pnl_pct:.1f}% (손절 기준 {settings.STOP_LOSS_PCT}%)"
            })
        elif pnl_pct >= settings.TAKE_PROFIT_PCT:
            signals.append({
                "type": "TAKE_PROFIT",
                "signal": "익절매",
                "reason": f"수익률 {pnl_pct:.1f}% (익절 기준 {settings.TAKE_PROFIT_PCT}%)"
            })

    # 스코어 기반 신호 (손절/익절 미발생 시만 의미 있으나 모두 수집)
    if combined_score >= settings.BUY_THRESHOLD:
        signals.append({
            "type": "BUY",
            "signal": "매수",
            "reason": f"통합 점수 {combined_score:.1f}점 (임계값 {settings.BUY_THRESHOLD}점 이상)"
        })
    elif combined_score < settings.SELL_THRESHOLD:
        signals.append({
            "type": "SELL",
            "signal": "매도",
            "reason": f"통합 점수 {combined_score:.1f}점 (임계값 {settings.SELL_THRESHOLD}점 미만)"
        })

    return {
        "signals": signals,
        "primary_signal": signals[0] if signals else {"type": "HOLD", "signal": "보유", "reason": "조건 없음"},
        "has_signal": len(signals) > 0
    }
