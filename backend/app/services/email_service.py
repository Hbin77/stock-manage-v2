"""이메일 알림 서비스 (Gmail SMTP)"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from loguru import logger
from app.config.settings import settings


def send_sell_signal_email(signals: list[dict]) -> bool:
    """매도 신호 이메일 발송"""
    if not all([settings.EMAIL_USER, settings.EMAIL_APP_PASSWORD, settings.NOTIFICATION_EMAIL]):
        logger.warning("이메일 설정 미완료 (EMAIL_USER/EMAIL_APP_PASSWORD/NOTIFICATION_EMAIL). 발송 건너뜀.")
        return False

    try:
        tickers = [s["ticker"] for s in signals]
        subject = f"[주식 매도 알림] {', '.join(tickers)} 매도 신호 발생"

        html_body = _build_html_body(signals)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.EMAIL_USER
        msg["To"] = settings.NOTIFICATION_EMAIL
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.EMAIL_USER, settings.EMAIL_APP_PASSWORD)
            server.send_message(msg)

        logger.info(f"매도 신호 이메일 발송 완료 → {settings.NOTIFICATION_EMAIL} ({len(signals)}개 종목)")
        return True

    except Exception as e:
        logger.error(f"이메일 발송 실패: {e}")
        return False


def _signal_color(signal_type: str) -> str:
    return {
        "STOP_LOSS": "#e53e3e",
        "TAKE_PROFIT": "#38a169",
        "SELL": "#dd6b20",
    }.get(signal_type, "#718096")


def _pnl_color(pnl: float) -> str:
    return "#e53e3e" if pnl < 0 else "#38a169"


def _build_html_body(signals: list[dict]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    signal_rows = ""

    for s in signals:
        color = _signal_color(s.get("signal_type", ""))
        pnl = s.get("pnl_pct", 0.0)
        pnl_color = _pnl_color(pnl)
        tech_signals_html = ""
        for ts in s.get("tech_signals", [])[:3]:
            tech_signals_html += f'<li style="margin:2px 0; color:#4a5568;">{ts}</li>'

        risk_html = ""
        for rf in s.get("news_risk_factors", [])[:2]:
            risk_html += f'<li style="margin:2px 0; color:#4a5568;">{rf}</li>'

        signal_rows += f"""
        <div style="background:#fff; border:1px solid #e2e8f0; border-left:4px solid {color};
                    border-radius:8px; padding:20px; margin-bottom:16px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                <div>
                    <span style="font-size:22px; font-weight:700; color:#1a202c;">{s.get('ticker')}</span>
                    <span style="margin-left:8px; color:#718096; font-size:14px;">{s.get('name','')}</span>
                </div>
                <span style="background:{color}; color:#fff; padding:4px 12px;
                             border-radius:20px; font-size:13px; font-weight:600;">
                    {s.get('signal', '매도')}
                </span>
            </div>

            <table style="width:100%; border-collapse:collapse; margin-bottom:12px;">
                <tr>
                    <td style="padding:4px 8px; background:#f7fafc; border-radius:4px; font-size:13px;">
                        <strong>수익률</strong>
                        <span style="color:{pnl_color}; font-weight:600; margin-left:8px;">
                            {pnl:+.2f}%
                        </span>
                    </td>
                    <td style="padding:4px 8px; font-size:13px;">
                        <strong>현재가</strong>
                        <span style="margin-left:8px;">${s.get('current_price', 0):.2f}</span>
                    </td>
                    <td style="padding:4px 8px; font-size:13px;">
                        <strong>평균단가</strong>
                        <span style="margin-left:8px;">${s.get('avg_buy_price', 0):.2f}</span>
                    </td>
                </tr>
                <tr style="margin-top:4px;">
                    <td style="padding:4px 8px; font-size:13px;">
                        <strong>기술점수</strong>
                        <span style="margin-left:8px;">{s.get('tech_score', 0):.1f}점</span>
                    </td>
                    <td style="padding:4px 8px; font-size:13px;">
                        <strong>뉴스매도점수</strong>
                        <span style="margin-left:8px;">{s.get('news_sell_score', 0):.0f}점</span>
                    </td>
                    <td style="padding:4px 8px; font-size:13px;">
                        <strong>통합점수</strong>
                        <span style="margin-left:8px;">{s.get('combined_score', 0):.1f}점</span>
                    </td>
                </tr>
            </table>

            <div style="margin-bottom:8px; padding:10px; background:#fffaf0; border-radius:4px;">
                <strong style="font-size:13px; color:#744210;">매도 판단 근거</strong><br>
                <span style="font-size:13px; color:#4a5568; line-height:1.6;">{s.get('reasoning', '')}</span>
            </div>

            {"<div style='margin-bottom:8px;'><strong style='font-size:13px;'>기술적 신호</strong><ul style='margin:4px 0; padding-left:20px;'>" + tech_signals_html + "</ul></div>" if tech_signals_html else ""}

            {"<div><strong style='font-size:13px;'>뉴스 리스크</strong><ul style='margin:4px 0; padding-left:20px;'>" + risk_html + "</ul></div>" if risk_html else ""}

            {"<div style='margin-top:8px; padding:8px; background:#f0fff4; border-radius:4px; font-size:13px; color:#276749;'><strong>뉴스 분석:</strong> " + s.get('news_reasoning', '') + "</div>" if s.get('news_reasoning') else ""}
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
                 background:#f7fafc; padding:20px; margin:0;">
        <div style="max-width:680px; margin:0 auto;">
            <div style="background:linear-gradient(135deg,#1a202c 0%,#2d3748 100%);
                        color:#fff; padding:24px; border-radius:12px 12px 0 0; margin-bottom:0;">
                <h1 style="margin:0; font-size:20px;">📊 주식 매도 신호 알림</h1>
                <p style="margin:8px 0 0; color:#a0aec0; font-size:14px;">{now} 기준 | {len(signals)}개 종목 매도 신호</p>
            </div>

            <div style="background:#fff3cd; padding:12px 20px; border-left:4px solid #f6c23e; margin-bottom:16px;">
                <p style="margin:0; font-size:13px; color:#856404;">
                    ⚠️ 이 알림은 자동 분석 결과입니다. 최종 매도 결정은 반드시 직접 판단하세요.
                </p>
            </div>

            {signal_rows}

            <div style="text-align:center; padding:16px; color:#a0aec0; font-size:12px;">
                S&P 500 AI 주식 추천 시스템 — 자동 발송
            </div>
        </div>
    </body>
    </html>
    """
