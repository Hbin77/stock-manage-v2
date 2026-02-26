"""Server-Sent Events (SSE) 실시간 스트림 API"""
import asyncio
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from loguru import logger

router = APIRouter()


async def event_stream():
    """Redis Pub/Sub을 통한 실시간 이벤트 스트리밍"""
    try:
        import redis.asyncio as aioredis
        from app.config.settings import settings

        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("stock_events")

        # 연결 확인 이벤트
        yield f"data: {json.dumps({'type': 'connected', 'message': '실시간 연결 성공'})}\n\n"

        async for message in pubsub.listen():
            if message["type"] == "message":
                yield f"data: {message['data']}\n\n"
            await asyncio.sleep(0.01)

    except Exception as e:
        logger.error(f"SSE 스트림 오류: {e}")
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"


async def heartbeat_stream():
    """Redis 없이 heartbeat만 전송 (폴백)"""
    count = 0
    while True:
        yield f"data: {json.dumps({'type': 'heartbeat', 'count': count})}\n\n"
        count += 1
        await asyncio.sleep(30)


@router.get("/events", summary="SSE 실시간 이벤트 스트림")
async def sse_endpoint():
    """
    Server-Sent Events 스트림.
    매도 신호, 시장 상태 변경 등 실시간 알림 수신.
    """
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )
