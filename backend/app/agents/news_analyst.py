"""뉴스 감성 분석 에이전트 (Claude AI 사용)"""
import json
import re
import asyncio
from typing import Optional
import anthropic
from loguru import logger
from app.config.settings import settings


class NewsAnalystAgent:
    """Claude AI 기반 뉴스 감성 분석 에이전트"""

    SYSTEM_PROMPT = """당신은 주식 시장 뉴스 감성 분석 전문가입니다.
제공된 뉴스 헤드라인들을 분석하여 해당 주식의 투자 심리를 0-100 점수로 평가하세요.

점수 기준:
- 80-100: 매우 긍정적 (실적 어닝 서프라이즈, 신제품 출시, 대규모 계약, 애널리스트 목표가 대폭 상향)
- 60-79: 긍정적 (애널리스트 상향, 파트너십, 성장 전망, 시장 점유율 확대)
- 40-59: 중립 (뉴스 없음 또는 혼재된 신호, 일반적인 시장 정보)
- 20-39: 부정적 (실적 하회, 소송, 규제 이슈, 경쟁 심화)
- 0-19: 매우 부정적 (회계 부정, 대규모 손실, 경영 위기, 파산 위험)

반드시 아래 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{
    "news_score": <0-100 사이 숫자>,
    "sentiment": "매우긍정|긍정|중립|부정|매우부정 중 하나",
    "key_catalysts": ["주요 촉매 1", "주요 촉매 2"],
    "reasoning": "한국어로 100자 이내 분석 근거"
}"""

    PORTFOLIO_SELL_PROMPT = """당신은 포트폴리오 리스크 관리 전문가입니다.
이미 보유 중인 주식의 최근 뉴스를 분석하여 지금 매도해야 하는지 판단하세요.

매도 점수 기준 (0=매도 불필요, 100=즉시 매도):
- 80-100: 즉시 매도 권고 (회계 부정, 파산 위험, 핵심 사업 붕괴, 대규모 예상 밖 손실)
- 60-79: 매도 고려 (실적 대폭 하회, 목표주가 대규모 하향, 핵심 경영진 갑작스런 사임, 규제 제재 확정)
- 40-59: 관망 (단기 부정적이나 장기 펀더멘털 유지, 혼재된 신호)
- 20-39: 보유 유지 (일시적 이슈, 사업모델 건재, 회복 가능성)
- 0-19: 매도 불필요 (중립 또는 긍정적 뉴스)

반드시 아래 JSON 형식으로만 응답 (다른 텍스트 없이):
{
    "sell_score": <0-100 숫자>,
    "action": "즉시매도|매도고려|관망|보유유지|매도불필요 중 하나",
    "risk_factors": ["핵심 리스크 1", "핵심 리스크 2"],
    "reasoning": "한국어로 150자 이내 매도 판단 근거"
}"""

    def __init__(self):
        self._client: Optional[anthropic.Anthropic] = None

    def _get_client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        return self._client

    def _is_permanent_error(self, error: Exception) -> bool:
        """재시도해도 해결 안 되는 영구 오류 판별 (크레딧 부족, 인증 실패 등)"""
        error_str = str(error).lower()
        permanent_keywords = [
            "credit balance is too low",
            "insufficient balance",
            "billing",
            "payment required",
            "invalid_request_error",
            "authentication",
            "unauthorized",
            "forbidden",
            "invalid api key",
        ]
        if any(kw in error_str for kw in permanent_keywords):
            return True
        if hasattr(error, "status_code") and error.status_code in [400, 401, 403]:
            return True
        return False

    async def analyze(self, ticker: str, headlines: list[str]) -> dict:
        """뉴스 헤드라인 감성 분석 (0-100 점수 반환)"""
        if not headlines:
            return {
                "news_score": 50.0,
                "sentiment": "중립",
                "key_catalysts": [],
                "reasoning": "분석 가능한 최근 뉴스 없음",
                "news_available": True,
            }

        if not settings.ANTHROPIC_API_KEY:
            logger.warning("ANTHROPIC_API_KEY가 설정되지 않았습니다.")
            return _fallback_result("API 키 없음")

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._call_claude, ticker, headlines)
            return result
        except Exception as e:
            logger.error(f"{ticker} 뉴스 분석 실패: {e}")
            return _fallback_result(f"분석 오류: {str(e)[:50]}")

    def _call_claude(self, ticker: str, headlines: list[str]) -> dict:
        """Claude API 동기 호출 (영구 오류는 즉시 중단, 일시 오류만 재시도)"""
        client = self._get_client()
        headlines_text = "\n".join([f"- {h}" for h in headlines[:10]])

        for attempt in range(3):
            try:
                message = client.messages.create(
                    model=settings.CLAUDE_MODEL,
                    max_tokens=512,
                    system=self.SYSTEM_PROMPT,
                    messages=[{
                        "role": "user",
                        "content": f"종목: {ticker}\n\n최근 뉴스 헤드라인:\n{headlines_text}"
                    }]
                )

                text = message.content[0].text.strip()
                try:
                    result = json.loads(text)
                except json.JSONDecodeError:
                    match = re.search(r'\{[\s\S]*\}', text)
                    if match:
                        result = json.loads(match.group())
                    else:
                        raise ValueError(f"JSON 파싱 실패: {text[:100]}")

                result["news_available"] = True
                return result

            except Exception as e:
                # 크레딧 부족 등 영구 오류 → 즉시 중단 (재시도 의미 없음)
                if self._is_permanent_error(e):
                    logger.error(f"{ticker} Anthropic 영구 오류 (재시도 중단): {str(e)[:80]}")
                    return _fallback_result("API 크레딧 부족 - Anthropic 콘솔에서 충전 필요")

                # 일시적 오류만 재시도
                logger.warning(f"{ticker} Claude 호출 시도 {attempt+1}/3 실패: {e}")
                if attempt < 2:
                    import time
                    time.sleep(2 ** attempt)

        return _fallback_result("분석 재시도 한도 초과")

    async def analyze_batch(self, ticker_headlines: dict[str, list[str]], max_concurrent: int = 5) -> dict[str, dict]:
        """여러 종목 뉴스 분석 (동시 처리 제한)"""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def analyze_with_semaphore(ticker: str, headlines: list[str]):
            async with semaphore:
                result = await self.analyze(ticker, headlines)
                return ticker, result

        tasks = [
            analyze_with_semaphore(ticker, headlines)
            for ticker, headlines in ticker_headlines.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            ticker: result
            for ticker, result in results
            if not isinstance(result, Exception)
        }

    async def analyze_for_portfolio(self, ticker: str, headlines: list[str]) -> dict:
        """보유 종목 매도 관점 뉴스 분석"""
        if not headlines:
            return {
                "sell_score": 25.0,
                "action": "보유유지",
                "risk_factors": [],
                "reasoning": "분석 가능한 최근 뉴스 없음 — 뉴스 기반 매도 신호 없음",
                "news_available": False,
            }

        if not settings.ANTHROPIC_API_KEY:
            return _portfolio_fallback("API 키 없음")

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._call_claude_portfolio, ticker, headlines)
            return result
        except Exception as e:
            logger.error(f"{ticker} 포트폴리오 뉴스 분석 실패: {e}")
            return _portfolio_fallback(f"분석 오류: {str(e)[:50]}")

    def _call_claude_portfolio(self, ticker: str, headlines: list[str]) -> dict:
        """Claude API 매도 관점 분석 호출"""
        client = self._get_client()
        headlines_text = "\n".join([f"- {h}" for h in headlines[:10]])

        for attempt in range(3):
            try:
                message = client.messages.create(
                    model=settings.CLAUDE_MODEL,
                    max_tokens=512,
                    system=self.PORTFOLIO_SELL_PROMPT,
                    messages=[{
                        "role": "user",
                        "content": f"보유 종목: {ticker}\n\n최근 뉴스:\n{headlines_text}\n\n이 종목을 지금 매도해야 할까요?"
                    }]
                )

                text = message.content[0].text.strip()
                try:
                    result = json.loads(text)
                except json.JSONDecodeError:
                    match = re.search(r'\{[\s\S]*\}', text)
                    if match:
                        result = json.loads(match.group())
                    else:
                        raise ValueError(f"JSON 파싱 실패: {text[:100]}")

                result["news_available"] = True
                return result

            except Exception as e:
                if self._is_permanent_error(e):
                    logger.error(f"{ticker} Anthropic 영구 오류: {str(e)[:80]}")
                    return _portfolio_fallback("API 크레딧 부족")

                logger.warning(f"{ticker} 포트폴리오 분석 시도 {attempt+1}/3 실패: {e}")
                if attempt < 2:
                    import time
                    time.sleep(2 ** attempt)

        return _portfolio_fallback("재시도 한도 초과")

    async def analyze_batch_for_portfolio(
        self, ticker_headlines: dict[str, list[str]], max_concurrent: int = 3
    ) -> dict[str, dict]:
        """여러 보유 종목 매도 관점 뉴스 분석"""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def analyze_with_semaphore(ticker: str, headlines: list[str]):
            async with semaphore:
                result = await self.analyze_for_portfolio(ticker, headlines)
                return ticker, result

        tasks = [
            analyze_with_semaphore(ticker, headlines)
            for ticker, headlines in ticker_headlines.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            ticker: result
            for ticker, result in results
            if not isinstance(result, Exception)
        }


def _fallback_result(reason: str) -> dict:
    """뉴스 분석 불가 시 반환 (news_available=False 플래그 포함)"""
    return {
        "news_score": 50.0,
        "sentiment": "중립",
        "key_catalysts": [],
        "reasoning": reason,
        "news_available": False,
    }


def _portfolio_fallback(reason: str) -> dict:
    """포트폴리오 뉴스 분석 불가 시 기본값 (보유유지 가정)"""
    return {
        "sell_score": 25.0,
        "action": "보유유지",
        "risk_factors": [],
        "reasoning": reason,
        "news_available": False,
    }
