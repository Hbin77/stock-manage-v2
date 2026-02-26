"""Celery 앱 설정"""
from celery import Celery
from app.config.settings import settings

celery_app = Celery(
    "stock_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.sell_analysis"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/New_York",
    enable_utc=True,
    beat_schedule={
        "sell-analysis-every-10-minutes": {
            "task": "app.tasks.sell_analysis.run_sell_analysis",
            "schedule": 600,  # 10분 = 600초
        }
    },
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)
