"""기술적 지표 계산 서비스 - 연속 스케일 점수로 종목 차별화"""
from typing import Optional
import pandas as pd
import numpy as np
import ta
from loguru import logger


def calculate_rsi(close: pd.Series, window: int = 14) -> Optional[float]:
    try:
        rsi = ta.momentum.RSIIndicator(close=close, window=window).rsi()
        return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None
    except Exception as e:
        logger.error(f"RSI 계산 실패: {e}")
        return None


def calculate_macd(close: pd.Series) -> dict:
    try:
        macd_ind = ta.trend.MACD(close=close, window_slow=26, window_fast=12, window_sign=9)
        return {
            "macd": float(macd_ind.macd().iloc[-1]),
            "signal": float(macd_ind.macd_signal().iloc[-1]),
            "hist": float(macd_ind.macd_diff().iloc[-1]),
            "macd_prev": float(macd_ind.macd().iloc[-2]),
            "signal_prev": float(macd_ind.macd_signal().iloc[-2]),
        }
    except Exception as e:
        logger.error(f"MACD 계산 실패: {e}")
        return {"macd": 0, "signal": 0, "hist": 0, "macd_prev": 0, "signal_prev": 0}


def calculate_bollinger_bands(close: pd.Series, window: int = 20) -> dict:
    try:
        bb = ta.volatility.BollingerBands(close=close, window=window)
        upper = float(bb.bollinger_hband().iloc[-1])
        lower = float(bb.bollinger_lband().iloc[-1])
        middle = float(bb.bollinger_mavg().iloc[-1])
        current = float(close.iloc[-1])
        band_width = upper - lower
        position = (current - lower) / band_width if band_width > 0 else 0.5
        return {"upper": upper, "middle": middle, "lower": lower, "position": position}
    except Exception as e:
        logger.error(f"볼린저밴드 계산 실패: {e}")
        return {"upper": 0, "middle": 0, "lower": 0, "position": 0.5}


def calculate_moving_averages(close: pd.Series) -> dict:
    try:
        ma20 = float(close.rolling(20).mean().iloc[-1])
        ma50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else None
        ma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None
        current = float(close.iloc[-1])
        return {"ma20": ma20, "ma50": ma50, "ma200": ma200, "current": current}
    except Exception as e:
        logger.error(f"이동평균 계산 실패: {e}")
        return {"ma20": None, "ma50": None, "ma200": None, "current": None}


def calculate_volume_signal(volume: pd.Series) -> dict:
    try:
        vol_current = float(volume.iloc[-1])
        vol_ma20 = float(volume.rolling(20).mean().iloc[-1])
        ratio = vol_current / vol_ma20 if vol_ma20 > 0 else 1.0
        return {"current": vol_current, "ma20": vol_ma20, "ratio": ratio}
    except Exception as e:
        logger.error(f"거래량 계산 실패: {e}")
        return {"current": 0, "ma20": 0, "ratio": 1.0}


# ──────────────────────────────────────────────
# 연속 점수 함수 (이산 버킷 대신 연속값 사용)
# ──────────────────────────────────────────────

def _rsi_score(rsi: Optional[float]) -> float:
    """RSI → 0-25점 (연속)"""
    if rsi is None:
        return 12.5
    if rsi < 30:
        return 18.0 + min(10.0, rsi * 0.4)     # 0→0, 30→18 방향 (극단 과매도)
    elif rsi < 40:
        return 18.0 + (rsi - 30) * 0.5         # 30→18, 40→23
    elif rsi < 50:
        return 23.0 - (rsi - 40) * 0.3         # 40→23, 50→20
    elif rsi < 60:
        return 20.0 - (rsi - 50) * 0.3         # 50→20, 60→17
    elif rsi < 70:
        return 17.0 - (rsi - 60) * 0.4         # 60→17, 70→13
    else:
        return max(3.0, 13.0 - (rsi - 70) * 0.5)  # 70→13 점점 감소


def _macd_score(macd_data: dict) -> float:
    """MACD → 0-25점 (연속, 히스토그램 크기 반영)"""
    macd = macd_data["macd"]
    signal = macd_data["signal"]
    hist = macd_data["hist"]
    macd_prev = macd_data["macd_prev"]
    signal_prev = macd_data["signal_prev"]

    # 골든크로스 (데드크로스에서 반전)
    if macd_prev <= signal_prev and macd > signal:
        return 25.0

    # 데드크로스 (골든크로스에서 반전)
    if macd_prev >= signal_prev and macd < signal:
        return 3.0

    # 둘 다 양수 영역 - 히스토그램 강도 반영
    if macd > 0 and signal > 0:
        max_val = max(abs(macd), abs(signal), 0.0001)
        norm = min(1.0, abs(hist) / max_val)
        return 17.0 + norm * 8.0   # 17-25점

    # MACD > signal이지만 완전한 강세 아님
    if macd > signal:
        # 신호선 차이 크기로 차별화
        diff_ratio = min(1.0, abs(hist) / (abs(signal) + 0.0001))
        return 10.0 + diff_ratio * 4.0  # 10-14점

    # MACD < signal (약세)
    return max(3.0, 8.0 - abs(hist) / (abs(signal) + 0.0001) * 5.0)


def _bb_score(position: Optional[float]) -> float:
    """볼린저밴드 위치 → 0-20점 (포물선, 하단=고점수)"""
    if position is None:
        return 10.0
    # 포물선: lower(0) → 20점, upper(1) → 0점
    score = 20.0 * (1.0 - (position ** 2))
    return max(0.0, min(20.0, score))


def _ma_score(ma_data: dict) -> float:
    """이동평균 정렬 → 0-20점 (거리 기반)"""
    current = ma_data.get("current")
    ma20 = ma_data.get("ma20")
    ma50 = ma_data.get("ma50")
    ma200 = ma_data.get("ma200")

    if not all([current, ma20]):
        return 10.0

    base = 2.0

    # 가격 > MA20 (최대 +8점)
    if current > ma20:
        strength = min(1.0, (current - ma20) / (ma20 * 0.05))
        base += 8.0 * strength

    # MA20 > MA50 (최대 +5점)
    if ma50 and ma20 > ma50:
        strength = min(1.0, (ma20 - ma50) / (ma50 * 0.03))
        base += 5.0 * strength

    # MA50 > MA200 완전 정배열 (최대 +7점)
    if ma200 and ma50 and ma50 > ma200:
        strength = min(1.0, (ma50 - ma200) / (ma200 * 0.05))
        base += 7.0 * strength

    return min(20.0, base)


def _volume_score(vol_data: dict) -> float:
    """거래량 비율 → 0-10점 (로그 스케일)"""
    ratio = vol_data.get("ratio", 1.0)
    if ratio <= 1.0:
        return 2.0
    # log2: ratio=1→2점, ratio=2→10점
    log_ratio = np.log2(ratio)
    score = 2.0 + 8.0 * min(1.0, log_ratio)
    return min(10.0, score)


def calculate_tech_score(df: pd.DataFrame) -> float:
    """
    기술적 지표 기반 0-100 점수 (연속 스케일링으로 종목 차별화)

    - RSI (25점): 연속 함수, 0.01점 단위 차별화
    - MACD (25점): 히스토그램 강도 반영
    - 볼린저밴드 (20점): 포물선 함수
    - 이동평균 (20점): 거리 기반
    - 거래량 (10점): 로그 스케일
    """
    if df is None or df.empty or len(df) < 20:
        return 50.0

    try:
        close = df["close"]
        volume = df["volume"]

        rsi = calculate_rsi(close)
        macd_data = calculate_macd(close)
        bb_data = calculate_bollinger_bands(close)
        ma_data = calculate_moving_averages(close)
        vol_data = calculate_volume_signal(volume)

        score = (
            _rsi_score(rsi)
            + _macd_score(macd_data)
            + _bb_score(bb_data["position"])
            + _ma_score(ma_data)
            + _volume_score(vol_data)
        )

        # ── 베어리시 신호 페널티 (점수-신호 연결) ─────────────────
        # MACD 데드크로스: -8점
        if macd_data["macd_prev"] >= macd_data["signal_prev"] and macd_data["macd"] < macd_data["signal"]:
            score -= 8.0
        # MACD 약세 지속: 히스토그램 크기 비례 패널티 (최대 -6점)
        elif macd_data["macd"] < macd_data["signal"]:
            signal_abs = abs(macd_data["signal"]) + 0.001
            hist_ratio = abs(macd_data["hist"]) / signal_abs
            score -= min(6.0, hist_ratio * 8.0)

        # MA20 하향 이탈: 이탈폭 비례 패널티 (1% 이탈시 -2점, 5%→-6점 최대)
        current_p = ma_data.get("current")
        ma20_p = ma_data.get("ma20")
        if current_p and ma20_p and current_p < ma20_p * 0.99:
            pct_below = (ma20_p - current_p) / ma20_p
            score -= min(6.0, pct_below * 120.0)

        # MA50 하향 이탈: 더 심각한 패널티 (최대 -10점)
        ma50_p = ma_data.get("ma50")
        if current_p and ma50_p and current_p < ma50_p * 0.99:
            pct_below = (ma50_p - current_p) / ma50_p
            score -= min(10.0, pct_below * 150.0)

        return round(min(100.0, max(0.0, score)), 2)

    except Exception as e:
        logger.error(f"기술적 점수 계산 실패: {e}")
        return 50.0


def calculate_all_indicators(df: pd.DataFrame) -> dict:
    """모든 기술적 지표 + 점수 계산"""
    if df is None or df.empty:
        return {}

    close = df["close"]
    volume = df["volume"]

    rsi = calculate_rsi(close)
    macd_data = calculate_macd(close)
    bb_data = calculate_bollinger_bands(close)
    ma_data = calculate_moving_averages(close)
    vol_data = calculate_volume_signal(volume)
    tech_score = calculate_tech_score(df)

    return {
        "rsi_14": rsi,
        "macd": macd_data.get("macd"),
        "macd_signal": macd_data.get("signal"),
        "macd_hist": macd_data.get("hist"),
        "bb_upper": bb_data.get("upper"),
        "bb_middle": bb_data.get("middle"),
        "bb_lower": bb_data.get("lower"),
        "ma_20": ma_data.get("ma20"),
        "ma_50": ma_data.get("ma50"),
        "ma_200": ma_data.get("ma200"),
        "volume_ma_20": vol_data.get("ma20"),
        "tech_score": tech_score,
    }


def detect_bearish_signals(df: pd.DataFrame) -> dict:
    """
    포트폴리오 보유 종목의 기술적 매도 신호 감지

    Returns:
        signals: 감지된 베어리시 신호 목록 (type, severity, description)
        high_severity_count: HIGH 등급 신호 수
        indicators: 주요 지표 값
    """
    if df is None or df.empty or len(df) < 20:
        return {"signals": [], "count": 0, "high_severity_count": 0, "indicators": {}}

    try:
        close = df["close"]
        volume = df["volume"]
        signals = []

        rsi = calculate_rsi(close)
        macd_data = calculate_macd(close)
        bb_data = calculate_bollinger_bands(close)
        ma_data = calculate_moving_averages(close)
        vol_data = calculate_volume_signal(volume)

        current_price = float(close.iloc[-1])
        ma20 = ma_data.get("ma20")
        ma50 = ma_data.get("ma50")
        ma200 = ma_data.get("ma200")

        # 1. MACD 데드크로스 (골든크로스→데드크로스 전환)
        if macd_data["macd_prev"] >= macd_data["signal_prev"] and macd_data["macd"] < macd_data["signal"]:
            signals.append({
                "type": "MACD_DEATH_CROSS",
                "severity": "HIGH",
                "description": f"MACD 데드크로스 발생 (MACD {macd_data['macd']:.3f} < 시그널 {macd_data['signal']:.3f}) — 단기 하락 전환",
            })
        elif macd_data["macd"] < macd_data["signal"]:
            # 상대값 기준 임계값: 시그널 크기의 5% 이상 乖離 (주가 독립적)
            signal_abs = abs(macd_data["signal"]) if macd_data["signal"] != 0 else 0.1
            relative_threshold = max(0.05, signal_abs * 0.05)
            if macd_data["hist"] < -relative_threshold:
                signals.append({
                    "type": "MACD_BEARISH",
                    "severity": "MEDIUM",
                    "description": f"MACD 약세 지속 (히스토그램 {macd_data['hist']:.3f}) — 매도 압력 우위",
                })

        # 2. RSI 과매수 (조정 위험)
        if rsi and rsi >= 72:
            signals.append({
                "type": "RSI_OVERBOUGHT",
                "severity": "MEDIUM",
                "description": f"RSI {rsi:.1f} 과매수 구간 (72 이상) — 단기 조정 가능성",
            })

        # 3. MA20 하향 이탈 (단기 추세 전환) - 1% 기준으로 노이즈 필터링
        if ma20 and current_price < ma20 * 0.99:
            pct = (ma20 - current_price) / ma20 * 100
            signals.append({
                "type": "BELOW_MA20",
                "severity": "MEDIUM",
                "description": f"MA20 하향 이탈 (현재가 MA20 대비 -{pct:.1f}%) — 단기 추세 약화",
            })

        # 4. MA50 하향 이탈 (중기 추세 전환, 더 심각) - 1% 기준
        if ma50 and current_price < ma50 * 0.99:
            pct = (ma50 - current_price) / ma50 * 100
            signals.append({
                "type": "BELOW_MA50",
                "severity": "HIGH",
                "description": f"MA50 하향 이탈 (현재가 MA50 대비 -{pct:.1f}%) — 중기 추세 전환 확인",
            })

        # 5. MA50/MA200 데스 크로스 (장기 하락세)
        if ma50 and ma200 and ma50 < ma200:
            pct = (ma200 - ma50) / ma200 * 100
            signals.append({
                "type": "DEATH_CROSS_50_200",
                "severity": "HIGH",
                "description": f"MA50/MA200 데스 크로스 (MA50 MA200 대비 -{pct:.1f}%) — 장기 하락 추세",
            })

        # 6. 볼린저밴드 하단 이탈 (강한 매도 압력)
        if bb_data["position"] < 0.05:
            signals.append({
                "type": "BB_LOWER_BREAK",
                "severity": "MEDIUM",
                "description": f"볼린저밴드 하단 이탈 (밴드 내 위치 {bb_data['position']:.2f}) — 강한 매도 압력",
            })

        # 7. 고거래량 하락 (기관 분배 신호)
        if vol_data.get("ratio", 1.0) > 1.5 and len(close) >= 2 and close.iloc[-1] < close.iloc[-2]:
            signals.append({
                "type": "HIGH_VOLUME_DECLINE",
                "severity": "MEDIUM",
                "description": f"고거래량 하락 (평균 대비 {vol_data['ratio']:.1f}배 거래량) — 기관 분배 가능성",
            })

        # HIGH 우선 정렬
        severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        signals.sort(key=lambda x: severity_order.get(x["severity"], 9))
        high_count = sum(1 for s in signals if s["severity"] == "HIGH")

        return {
            "signals": signals,
            "count": len(signals),
            "high_severity_count": high_count,
            "indicators": {
                "rsi": rsi,
                "macd": macd_data["macd"],
                "macd_signal": macd_data["signal"],
                "macd_hist": macd_data["hist"],
                "bb_position": bb_data["position"],
                "ma20": ma20,
                "ma50": ma50,
                "ma200": ma200,
                "current_price": current_price,
                "volume_ratio": vol_data.get("ratio"),
            },
        }
    except Exception as e:
        logger.error(f"베어리시 신호 감지 실패: {e}")
        return {"signals": [], "count": 0, "high_severity_count": 0, "indicators": {}}


def calculate_scalp_entry_score(df: pd.DataFrame) -> dict:
    """
    단타 전용 진입 점수 및 조건 검증 (3개월 데이터 사용)

    가중치:
      - RSI 모멘텀   (30점): RSI 45-68 구간에서 상승 모멘텀
      - MACD 가속도  (35점): 히스토그램 양수 + 개선 추세
      - MA 정배열    (25점): 현재가 > MA20 > MA50
      - Volume 확인  (10점): 거래량 >= 1.3× MA20

    Returns:
        entry_score (0-100), validation dict, all_conditions_pass flag
    """
    if df is None or df.empty or len(df) < 55:
        return {
            "entry_score": 0.0,
            "rsi_score": 0.0,
            "macd_score": 0.0,
            "ma_score": 0.0,
            "volume_score": 0.0,
            "validation": {
                "rsi_ok": False, "macd_positive": False,
                "macd_improving": False, "above_ma20": False,
                "above_ma50": False, "volume_ok": False,
            },
            "all_conditions_pass": False,
            "rsi": None, "macd_hist_today": None,
            "macd_hist_yesterday": None, "volume_ratio": None,
        }

    try:
        close = df["close"]
        volume = df["volume"]

        # ── 지표 계산 ──────────────────────────────────────────
        rsi = calculate_rsi(close)
        macd_data = calculate_macd(close)
        ma_data = calculate_moving_averages(close)
        vol_data = calculate_volume_signal(volume)

        current_price = float(close.iloc[-1])
        ma20 = ma_data.get("ma20")
        ma50 = ma_data.get("ma50")
        volume_ratio = vol_data.get("ratio", 1.0)

        hist_today = macd_data["hist"]
        hist_yesterday = macd_data.get("macd_prev", 0) - macd_data.get("signal_prev", 0)

        # ── 조건 검증 ─────────────────────────────────────────
        rsi_ok = rsi is not None and 45.0 <= rsi <= 68.0
        macd_positive = hist_today > 0
        macd_improving = hist_today > hist_yesterday
        above_ma20 = ma20 is not None and current_price > ma20
        above_ma50 = ma50 is not None and current_price > ma50
        volume_ok = volume_ratio >= 1.3

        validation = {
            "rsi_ok": rsi_ok,
            "macd_positive": macd_positive,
            "macd_improving": macd_improving,
            "above_ma20": above_ma20,
            "above_ma50": above_ma50,
            "volume_ok": volume_ok,
        }

        all_conditions_pass = all(validation.values())

        # ── RSI 모멘텀 점수 (0-30) ────────────────────────────
        if rsi_ok and rsi is not None:
            rsi_score = 15.0 + (rsi - 45.0) / (68.0 - 45.0) * 15.0
        else:
            rsi_score = 0.0

        # ── MACD 가속도 점수 (0-35) ───────────────────────────
        if not macd_positive:
            macd_score = 0.0
        elif not macd_improving:
            macd_score = 10.0  # 양수지만 개선 없음
        else:
            # 히스토그램 크기 기반 강도 계산
            norm = min(1.0, abs(hist_today) / (abs(current_price) * 0.002 + 0.0001))
            macd_score = 20.0 + norm * 10.0
            # 연속 2일 개선 보너스 (+5점)
            try:
                macd_ind = ta.trend.MACD(close=close, window_slow=26, window_fast=12, window_sign=9)
                diffs = macd_ind.macd_diff()
                if len(diffs) >= 3 and diffs.iloc[-2] > diffs.iloc[-3]:
                    macd_score = min(35.0, macd_score + 5.0)
            except Exception:
                pass
            macd_score = min(35.0, macd_score)

        # ── MA 정배열 점수 (0-25) ─────────────────────────────
        if not above_ma20 or not above_ma50:
            ma_align_score = 0.0
        else:
            dist20 = (current_price - ma20) / ma20 if ma20 else 0
            dist50 = (current_price - ma50) / ma50 if ma50 else 0
            ma_align_score = 12.0 + min(8.0, dist20 / 0.02 * 8.0) + min(5.0, dist50 / 0.03 * 5.0)
            ma_align_score = min(25.0, ma_align_score)

        # ── 거래량 점수 (0-10) ────────────────────────────────
        if not volume_ok:
            vol_score = 0.0
        else:
            vol_score = min(10.0, 5.0 + (volume_ratio - 1.3) / 0.7 * 5.0)

        entry_score = round(rsi_score + macd_score + ma_align_score + vol_score, 2)

        return {
            "entry_score": entry_score,
            "rsi_score": round(rsi_score, 2),
            "macd_score": round(macd_score, 2),
            "ma_score": round(ma_align_score, 2),
            "volume_score": round(vol_score, 2),
            "validation": validation,
            "all_conditions_pass": all_conditions_pass,
            "rsi": rsi,
            "macd_hist_today": round(hist_today, 4),
            "macd_hist_yesterday": round(hist_yesterday, 4),
            "volume_ratio": round(volume_ratio, 2),
            "current_price": current_price,
            "ma20": ma20,
            "ma50": ma50,
        }

    except Exception as e:
        logger.error(f"단타 진입 점수 계산 실패: {e}")
        return {
            "entry_score": 0.0,
            "rsi_score": 0.0, "macd_score": 0.0,
            "ma_score": 0.0, "volume_score": 0.0,
            "validation": {
                "rsi_ok": False, "macd_positive": False,
                "macd_improving": False, "above_ma20": False,
                "above_ma50": False, "volume_ok": False,
            },
            "all_conditions_pass": False,
            "rsi": None, "macd_hist_today": None,
            "macd_hist_yesterday": None, "volume_ratio": None,
        }
