"""NYSE 거래 시간 및 휴장일 확인 서비스"""
from datetime import datetime, time
from zoneinfo import ZoneInfo
from loguru import logger

EASTERN_TZ = ZoneInfo("America/New_York")
MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)


def get_market_time() -> datetime:
    """현재 미국 동부 시간 반환"""
    return datetime.now(EASTERN_TZ)


def is_market_open() -> bool:
    """현재 NYSE 장 운영 중 여부 확인 (9:30 AM - 4:00 PM EST)"""
    now = get_market_time()
    if not _is_nyse_trading_day(now):
        return False
    return MARKET_OPEN <= now.time() <= MARKET_CLOSE


def get_market_status() -> dict:
    """시장 상태 상세 정보 반환"""
    now = get_market_time()
    is_open = is_market_open()
    is_trading_day = _is_nyse_trading_day(now)

    status = {
        "is_open": is_open,
        "is_trading_day": is_trading_day,
        "current_time_est": now.strftime("%Y-%m-%d %H:%M:%S EST"),
        "market_open": "09:30 EST",
        "market_close": "16:00 EST",
    }

    if is_open:
        status["message"] = "장 운영 중"
    elif is_trading_day and now.time() < MARKET_OPEN:
        status["message"] = "장 시작 전"
    elif is_trading_day and now.time() > MARKET_CLOSE:
        status["message"] = "장 마감"
    else:
        status["message"] = "휴장일"

    return status


def _is_nyse_trading_day(now: datetime) -> bool:
    """NYSE 거래일 여부 확인 (주말 + 미국 공휴일 제외)"""
    # 주말 제외
    if now.weekday() >= 5:
        return False

    month = now.month
    day = now.day
    weekday = now.weekday()  # 0=Monday, 4=Friday

    # 고정 공휴일
    fixed_holidays = [
        (1, 1),   # 신년
        (6, 19),  # 준틴스
        (7, 4),   # 독립기념일
        (12, 25), # 크리스마스
    ]

    # 주말 대체 공휴일 처리
    for h_month, h_day in fixed_holidays:
        if month == h_month and day == h_day:
            return False
        # 토요일 공휴일 → 금요일 대체
        h_date = datetime(now.year, h_month, h_day, tzinfo=EASTERN_TZ)
        if h_date.weekday() == 5 and month == h_month and day == h_day - 1:
            return False
        # 일요일 공휴일 → 월요일 대체
        if h_date.weekday() == 6 and month == h_month and day == h_day + 1:
            return False

    # 변동 공휴일
    # MLK Day: 1월 셋째 월요일
    if month == 1 and weekday == 0 and 15 <= day <= 21:
        return False
    # 대통령의 날: 2월 셋째 월요일
    if month == 2 and weekday == 0 and 15 <= day <= 21:
        return False
    # 메모리얼 데이: 5월 마지막 월요일
    if month == 5 and weekday == 0 and day >= 25:
        return False
    # 노동절: 9월 첫째 월요일
    if month == 9 and weekday == 0 and day <= 7:
        return False
    # 추수감사절: 11월 넷째 목요일
    if month == 11 and weekday == 3 and 22 <= day <= 28:
        return False

    return True
