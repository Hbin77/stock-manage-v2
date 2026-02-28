"""포트폴리오 관리 에이전트 - 단타 트레일링/타임스톱 + 기술적/뉴스 심층 분석"""
import asyncio
from datetime import datetime, date, timedelta
from loguru import logger
from sqlalchemy import select, and_
from app.database.connection import AsyncSessionLocal
from app.database.models import PortfolioHolding, Stock, SellSignal
from app.agents.technical_analyst import TechnicalAnalystAgent
from app.agents.news_analyst import NewsAnalystAgent
from app.services.news_service import fetch_news
from app.services.market_data import fetch_current_price
from app.services.scoring import calculate_combined_score
from app.config.settings import settings


class PortfolioManagerAgent:
    """포트폴리오 매도 신호 감지 에이전트 — 단타 트레일링/타임스톱 + 기술적/뉴스 분석"""

    def __init__(self):
        self.technical_analyst = TechnicalAnalystAgent()
        self.news_analyst = NewsAnalystAgent()

    async def get_holdings(self) -> list[dict]:
        """현재 보유 종목 조회"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(PortfolioHolding, Stock)
                .join(Stock, PortfolioHolding.stock_id == Stock.id)
            )
            holdings = []
            for holding, stock in result.fetchall():
                holdings.append({
                    "id": holding.id,
                    "stock_id": holding.stock_id,
                    "ticker": stock.ticker,
                    "name": stock.name,
                    "quantity": holding.quantity,
                    "avg_buy_price": holding.avg_buy_price,
                    "total_invested": holding.total_invested,
                    "current_price": holding.current_price,
                    "unrealized_pnl": holding.unrealized_pnl,
                    "unrealized_pnl_pct": holding.unrealized_pnl_pct,
                    "first_bought_at": holding.first_bought_at.isoformat() if holding.first_bought_at else None,
                    # 단타 필드
                    "is_scalp_trade": getattr(holding, "is_scalp_trade", False),
                    "peak_price": getattr(holding, "peak_price", None),
                    "trailing_stop_active": getattr(holding, "trailing_stop_active", False),
                    "trailing_stop_price": getattr(holding, "trailing_stop_price", None),
                    "breakeven_locked": getattr(holding, "breakeven_locked", False),
                    "trading_days_held": getattr(holding, "trading_days_held", 0),
                })
            return holdings

    async def update_prices(self, holdings: list[dict]) -> list[dict]:
        """현재가 업데이트 + 단타 포지션의 peak_price/trailing_stop 갱신"""
        tickers = [h["ticker"] for h in holdings]
        prices = await asyncio.gather(
            *[fetch_current_price(t) for t in tickers],
            return_exceptions=True
        )

        async with AsyncSessionLocal() as session:
            for holding_data, price in zip(holdings, prices):
                if isinstance(price, Exception) or price is None:
                    continue

                current_price = float(price)
                avg_buy = holding_data["avg_buy_price"]
                quantity = holding_data["quantity"]

                pnl = (current_price - avg_buy) * quantity
                pnl_pct = ((current_price - avg_buy) / avg_buy) * 100 if avg_buy > 0 else 0.0

                holding_data["current_price"] = current_price
                holding_data["unrealized_pnl"] = round(pnl, 2)
                holding_data["unrealized_pnl_pct"] = round(pnl_pct, 2)

                result = await session.execute(
                    select(PortfolioHolding).where(PortfolioHolding.id == holding_data["id"])
                )
                holding_obj = result.scalar_one_or_none()
                if not holding_obj:
                    continue

                holding_obj.current_price = current_price
                holding_obj.unrealized_pnl = pnl
                holding_obj.unrealized_pnl_pct = pnl_pct

                # ── 단타 포지션: peak_price + trailing stop 갱신 ──────
                if getattr(holding_obj, "is_scalp_trade", False):
                    prev_peak = getattr(holding_obj, "peak_price", None) or avg_buy
                    new_peak = max(prev_peak, current_price)
                    holding_obj.peak_price = new_peak
                    holding_data["peak_price"] = new_peak

                    # Stage 1: +1.5% 달성 시 손절 → 매수가 이동 (breakeven lock)
                    if (pnl_pct >= settings.SCALP_BREAKEVEN_TRIGGER_PCT
                            and not getattr(holding_obj, "breakeven_locked", False)):
                        holding_obj.breakeven_locked = True
                        holding_obj.trailing_stop_price = avg_buy
                        holding_data["breakeven_locked"] = True
                        holding_data["trailing_stop_price"] = avg_buy
                        logger.info(
                            f"[{holding_data['ticker']}] 브레이크이븐 활성화: "
                            f"손절 → 매수가(${avg_buy:.2f}) 이동 (수익 {pnl_pct:.2f}%)"
                        )

                    # Stage 2: +2% 달성 시 트레일링 스톱 시작 (고점 -1%)
                    if pnl_pct >= settings.SCALP_TRAIL_TRIGGER_PCT:
                        holding_obj.trailing_stop_active = True
                        new_trail = new_peak * (1 - settings.SCALP_TRAIL_PCT / 100)
                        existing_trail = getattr(holding_obj, "trailing_stop_price", 0.0) or 0.0
                        if new_trail > existing_trail:
                            holding_obj.trailing_stop_price = new_trail
                            holding_data["trailing_stop_price"] = new_trail
                        holding_data["trailing_stop_active"] = True

                    # 거래일 수 갱신 (날짜가 바뀐 경우에만 +1)
                    await self._increment_trading_days(session, holding_obj, holding_data)

            await session.commit()

        return holdings

    async def _increment_trading_days(self, session, holding_obj, holding_data: dict):
        """거래일 변경 시 trading_days_held 증가"""
        try:
            from app.services.market_hours import is_market_open
            if not is_market_open():
                return
            last_updated = holding_obj.last_updated_at
            from zoneinfo import ZoneInfo
            today = datetime.now(ZoneInfo("America/New_York")).date()
            if last_updated is None or last_updated.date() < today:
                holding_obj.trading_days_held = getattr(holding_obj, "trading_days_held", 0) + 1
                holding_data["trading_days_held"] = holding_obj.trading_days_held
        except Exception as e:
            logger.warning(f"거래일 카운터 업데이트 실패: {e}")

    async def check_sell_signals(self) -> list[dict]:
        """
        포트폴리오 매도 신호 심층 분석

        단타 포지션 (is_scalp_trade=True):
          1. 단타 손절: -2% 이탈 (최우선 — 손실 방어)
          2. 단타 익절: +3% 달성 (목표 즉시 확정)
          3. 트레일링 스톱: 고점 -1% 이탈 시 청산 (이익 보호)
          4. 브레이크이븐 스톱: +1.5% 후 매수가 이탈 시 청산 (원금 보호)
          5. 타임스톱: 5거래일 경과 시 청산 (최후 안전장치)

        스윙 포지션 (is_scalp_trade=False):
          1. P&L 손절: pnl <= -5%
          2. P&L 익절: pnl >= +15%
          3. 기술적 강매도: HIGH 신호 2개 이상
          4. 기술적+뉴스 복합: HIGH 신호 + sell_score >= 55
          5. 뉴스 단독 매도: sell_score >= 70
          6. 통합점수 하락: combined_score < 40
        """
        holdings = await self.get_holdings()
        if not holdings:
            return {"sell_signals": [], "hold_analysis": []}

        holdings = await self.update_prices(holdings)
        tickers = [h["ticker"] for h in holdings]

        logger.info(f"포트폴리오 매도 분석 시작: {tickers}")

        # 기술적 분석 + 뉴스 수집 병렬 실행
        tech_results_raw, headlines_raw = await asyncio.gather(
            asyncio.gather(*[self.technical_analyst.analyze(t) for t in tickers], return_exceptions=True),
            asyncio.gather(*[fetch_news(t) for t in tickers], return_exceptions=True),
        )

        # 매도 관점 뉴스 분석
        ticker_headlines = {
            t: h if not isinstance(h, Exception) else []
            for t, h in zip(tickers, headlines_raw)
        }
        news_sell_results = await self.news_analyst.analyze_batch_for_portfolio(
            ticker_headlines, max_concurrent=3
        )

        sell_signals = []
        hold_analysis = []

        async with AsyncSessionLocal() as session:
            for holding, tech_result in zip(holdings, tech_results_raw):
                ticker = holding["ticker"]
                pnl_pct = holding.get("unrealized_pnl_pct", 0.0) or 0.0
                current_price = holding.get("current_price")
                avg_buy_price = holding["avg_buy_price"]
                is_scalp = holding.get("is_scalp_trade", False)

                # 기술적 분석 결과 파싱
                if isinstance(tech_result, Exception):
                    tech_score = 50.0
                    bearish = {"signals": [], "count": 0, "high_severity_count": 0}
                else:
                    tech_score = tech_result.get("tech_score", 50.0)
                    bearish = tech_result.get("bearish_signals", {
                        "signals": [], "count": 0, "high_severity_count": 0
                    })

                high_signals = [s for s in bearish.get("signals", []) if s["severity"] == "HIGH"]
                med_signals = [s for s in bearish.get("signals", []) if s["severity"] == "MEDIUM"]

                # 뉴스 매도 분석 결과 파싱
                news_data = news_sell_results.get(ticker, {
                    "sell_score": 25.0, "action": "보유유지",
                    "risk_factors": [], "reasoning": "분석 없음"
                })
                news_sell_score = news_data.get("sell_score", 25.0)
                news_score_for_combined = max(0, 100 - news_sell_score)
                combined_score = calculate_combined_score(tech_score, news_score_for_combined)

                signal_type = None
                signal_reasons = []

                # ══════════════════════════════════════════════════
                # 단타 포지션 전용 매도 로직
                # ══════════════════════════════════════════════════
                if is_scalp:
                    peak_price = holding.get("peak_price")
                    trailing_stop_price = holding.get("trailing_stop_price")
                    trailing_stop_active = holding.get("trailing_stop_active", False)
                    breakeven_locked = holding.get("breakeven_locked", False)
                    trading_days_held = holding.get("trading_days_held", 0)

                    # 1. 단타 손절 -2% (최우선 — 손실 방어)
                    if pnl_pct <= settings.SCALP_STOP_LOSS_PCT:
                        signal_type = "STOP_LOSS"
                        signal_reasons.append(
                            f"단타 손절: {pnl_pct:.2f}% (기준 {settings.SCALP_STOP_LOSS_PCT}%)"
                        )
                        if high_signals:
                            signal_reasons.append(high_signals[0]["description"])

                    # 2. 단타 익절 +3% (목표 달성 즉시 확정)
                    if not signal_type and pnl_pct >= settings.SCALP_TAKE_PROFIT_PCT:
                        signal_type = "TAKE_PROFIT"
                        signal_reasons.append(
                            f"단타 익절: +{pnl_pct:.2f}% 달성 (목표 +{settings.SCALP_TAKE_PROFIT_PCT}%)"
                        )

                    # 3. 트레일링 스톱 (고점 -1% 이탈 — 이익 보호)
                    if not signal_type and trailing_stop_active and trailing_stop_price and current_price:
                        if current_price <= trailing_stop_price:
                            signal_type = "TRAILING_STOP"
                            peak_str = f"${peak_price:.2f}" if peak_price else "-"
                            signal_reasons.append(
                                f"트레일링 스톱: 현재가 ${current_price:.2f} ≤ "
                                f"트레일가 ${trailing_stop_price:.2f} "
                                f"(고점 {peak_str} 대비 -1%) | 수익 확정"
                            )

                    # 4. 브레이크이븐 스톱 (매수가 이탈 — 원금 보호)
                    if not signal_type and breakeven_locked and trailing_stop_price and current_price:
                        if not trailing_stop_active and current_price <= trailing_stop_price:
                            signal_type = "BREAKEVEN_STOP"
                            signal_reasons.append(
                                f"브레이크이븐 스톱: 현재가 ${current_price:.2f} ≤ "
                                f"매수가 ${avg_buy_price:.2f} "
                                f"(+1.5% 이상 달성 후 원점 복귀 — 손실 방지)"
                            )

                    # 5. 타임스톱: 보유 5거래일 이상 (최후 안전장치)
                    if not signal_type and trading_days_held >= settings.SCALP_MAX_HOLDING_DAYS:
                        signal_type = "TIME_STOP"
                        signal_reasons.append(
                            f"타임스톱: {trading_days_held}거래일 보유 "
                            f"(최대 {settings.SCALP_MAX_HOLDING_DAYS}일) | "
                            f"현재 수익률 {pnl_pct:+.2f}%"
                        )

                    # 보유 유지: 이유 수집
                    if not signal_type:
                        trail_str = f"${trailing_stop_price:.2f}" if trailing_stop_price else "-"
                        peak_fmt = f"${peak_price:.2f}" if peak_price else "-"
                        logger.info(
                            f"[{ticker}] 단타 보유유지 | pnl={pnl_pct:+.2f}% | "
                            f"peak={peak_fmt} | "
                            f"trail={trail_str} | days={trading_days_held}"
                        )
                        hold_reasons = [f"수익률 {pnl_pct:+.2f}% — 손절 {settings.SCALP_STOP_LOSS_PCT}%/익절 +{settings.SCALP_TAKE_PROFIT_PCT}% 범위 내"]
                        if breakeven_locked:
                            hold_reasons.append("브레이크이븐 보호 활성화 (최소 0% 손실 보장)")
                        if trailing_stop_active and trailing_stop_price:
                            hold_reasons.append(f"트레일링 스톱 ${trailing_stop_price:.2f} 추적 중 (고점 대비 -1%)")
                        remaining = settings.SCALP_MAX_HOLDING_DAYS - trading_days_held
                        hold_reasons.append(f"잔여 보유기간 {remaining}거래일 (타임스톱까지)")
                        if high_signals:
                            hold_reasons.append(f"기술 경고: {high_signals[0]['description']}")
                        hold_analysis.append({
                            "ticker": ticker,
                            "name": holding["name"],
                            "decision": "HOLD",
                            "strategy": "SCALP",
                            "pnl_pct": round(pnl_pct, 2),
                            "current_price": current_price,
                            "avg_buy_price": avg_buy_price,
                            "tech_score": round(tech_score, 2),
                            "news_sell_score": round(news_sell_score, 2),
                            "news_action": news_data.get("action", ""),
                            "hold_reasons": hold_reasons,
                            "tech_signals": [s["description"] for s in bearish.get("signals", [])],
                            "peak_price": holding.get("peak_price"),
                            "trailing_stop_price": holding.get("trailing_stop_price"),
                            "trailing_stop_active": holding.get("trailing_stop_active", False),
                            "breakeven_locked": holding.get("breakeven_locked", False),
                            "trading_days_held": trading_days_held,
                        })
                        continue

                # ══════════════════════════════════════════════════
                # 스윙 포지션 매도 로직 (기존)
                # ══════════════════════════════════════════════════
                else:
                    # 1. 손절
                    if pnl_pct <= settings.STOP_LOSS_PCT:
                        signal_type = "STOP_LOSS"
                        signal_reasons.append(f"손실률 {pnl_pct:.1f}% — 손절 기준({settings.STOP_LOSS_PCT}%) 도달")

                    # 2. 익절
                    elif pnl_pct >= settings.TAKE_PROFIT_PCT:
                        signal_type = "TAKE_PROFIT"
                        signal_reasons.append(f"수익률 {pnl_pct:.1f}% — 익절 기준(+{settings.TAKE_PROFIT_PCT}%) 달성")

                    # 3. 기술적 강매도
                    if not signal_type and len(high_signals) >= 2:
                        signal_type = "SELL"
                        signal_reasons.extend([s["description"] for s in high_signals[:2]])

                    # 4. 복합 매도
                    if not signal_type and high_signals and news_sell_score >= settings.SWING_NEWS_COMBINED_THRESHOLD:
                        signal_type = "SELL"
                        signal_reasons.append(high_signals[0]["description"])
                        signal_reasons.append(
                            f"뉴스 매도 신호: {news_data.get('action','')} (sell_score {news_sell_score:.0f})"
                        )

                    # 5. 뉴스 단독 매도
                    if not signal_type and news_sell_score >= settings.SWING_NEWS_ALONE_THRESHOLD:
                        signal_type = "SELL"
                        signal_reasons.append(
                            f"뉴스 분석: {news_data.get('action','')} (sell_score {news_sell_score:.0f})"
                        )
                        signal_reasons.extend(news_data.get("risk_factors", [])[:2])

                    # 6. 통합점수 하락
                    if not signal_type and combined_score < settings.SELL_THRESHOLD:
                        signal_type = "SELL"
                        signal_reasons.append(
                            f"통합점수 {combined_score:.1f}점 — 매도 기준({settings.SELL_THRESHOLD}점) 미만"
                        )

                    # 보조 정보 추가
                    if signal_type and med_signals and len(signal_reasons) < 4:
                        signal_reasons.append(med_signals[0]["description"])

                    if not signal_type:
                        tech_summary = ", ".join(
                            [f"{s['type']}({s['severity']})" for s in bearish.get("signals", [])]
                        ) or "없음"
                        logger.info(
                            f"[{ticker}] 스윙 보유유지 | tech={tech_score:.1f} | "
                            f"bearish={tech_summary} | "
                            f"news_action={news_data.get('action','-')}(sell={news_sell_score:.0f}) | "
                            f"pnl={pnl_pct:.2f}%"
                        )
                        hold_reasons = [f"수익률 {pnl_pct:+.2f}% — 손절 {settings.STOP_LOSS_PCT}%/익절 +{settings.TAKE_PROFIT_PCT}% 범위 내"]
                        if tech_score >= 60:
                            hold_reasons.append(f"기술적 점수 양호: {tech_score:.1f}점")
                        if news_sell_score < 40:
                            hold_reasons.append(f"뉴스 매도 압력 낮음 (sell_score {news_sell_score:.0f})")
                        if combined_score >= settings.SELL_THRESHOLD:
                            hold_reasons.append(f"통합점수 {combined_score:.1f}점 — 매도 기준({settings.SELL_THRESHOLD}점) 이상")
                        if bearish.get("signals"):
                            hold_reasons.append(f"관찰 중: {bearish['signals'][0]['description']}")
                        hold_analysis.append({
                            "ticker": ticker,
                            "name": holding["name"],
                            "decision": "HOLD",
                            "strategy": "SWING",
                            "pnl_pct": round(pnl_pct, 2),
                            "current_price": current_price,
                            "avg_buy_price": avg_buy_price,
                            "tech_score": round(tech_score, 2),
                            "news_sell_score": round(news_sell_score, 2),
                            "combined_score": round(combined_score, 2),
                            "news_action": news_data.get("action", ""),
                            "news_reasoning": news_data.get("reasoning", ""),
                            "hold_reasons": hold_reasons,
                            "tech_signals": [s["description"] for s in bearish.get("signals", [])],
                        })
                        continue

                # ── 매도 신호 중복 방지 (24시간 내 동일 종목+신호 skip) ──
                cutoff_24h = datetime.utcnow() - timedelta(hours=24)
                dup_check = await session.execute(
                    select(SellSignal).where(
                        and_(
                            SellSignal.stock_id == holding["stock_id"],
                            SellSignal.signal_type == signal_type,
                            SellSignal.signal_at >= cutoff_24h,
                        )
                    )
                )
                if dup_check.scalars().first():
                    logger.info(
                        f"[{ticker}] 중복 신호 skip: {signal_type} "
                        f"(최근 24h 내 동일 신호 존재 — DB/이메일/UI 모두 skip)"
                    )
                    continue

                # ── 매도 신호 저장 ────────────────────────────────────
                signal_text = {
                    "STOP_LOSS": "손절매",
                    "TAKE_PROFIT": "익절매",
                    "SELL": "매도 권고",
                    "TIME_STOP": "타임스톱",
                    "TRAILING_STOP": "트레일링스톱",
                    "BREAKEVEN_STOP": "브레이크이븐",
                }.get(signal_type, "매도")

                full_reasoning = " | ".join(signal_reasons[:4])

                new_signal = SellSignal(
                    stock_id=holding["stock_id"],
                    signal_type=signal_type,
                    signal=signal_text,
                    combined_score=combined_score,
                    pnl_pct=pnl_pct,
                    reasoning=full_reasoning,
                    signal_at=datetime.utcnow(),
                )
                session.add(new_signal)

                sell_signals.append({
                    "ticker": ticker,
                    "name": holding["name"],
                    "signal_type": signal_type,
                    "signal": signal_text,
                    "combined_score": round(combined_score, 2),
                    "tech_score": round(tech_score, 2),
                    "news_sell_score": round(news_sell_score, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "current_price": current_price,
                    "avg_buy_price": avg_buy_price,
                    "peak_price": holding.get("peak_price"),
                    "trailing_stop_price": holding.get("trailing_stop_price"),
                    "trading_days_held": holding.get("trading_days_held", 0),
                    "is_scalp_trade": is_scalp,
                    "reasoning": full_reasoning,
                    "tech_signals": [s["description"] for s in bearish.get("signals", [])],
                    "news_action": news_data.get("action", ""),
                    "news_risk_factors": news_data.get("risk_factors", []),
                    "news_reasoning": news_data.get("reasoning", ""),
                })

                logger.warning(
                    f"[{ticker}] {'단타' if is_scalp else '스윙'} 매도신호! "
                    f"signal={signal_type} | pnl={pnl_pct:.2f}% | reasons: {full_reasoning}"
                )

            await session.commit()

        if sell_signals:
            logger.info(f"매도 신호 발생: {[s['ticker'] for s in sell_signals]}")

        return {"sell_signals": sell_signals, "hold_analysis": hold_analysis}
