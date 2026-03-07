from celery import Celery
from celery.schedules import crontab
from app.config import REDIS_URL

celery = Celery("memolens", broker=REDIS_URL, backend=REDIS_URL)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Periodic task: check time-based reminders every minute
celery.conf.beat_schedule = {
    "check-reminders-every-minute": {
        "task": "app.workers.celery_app.check_reminders",
        "schedule": crontab(minute="*"),
    },
}


@celery.task
def check_reminders():
    """
    Periodic task to check and trigger time-based reminders.
    In production, this would query the DB for reminders matching the current time
    and push notifications via WebSocket or push service.
    For the hackathon, time-based reminders are checked inline during WebSocket frames.
    """
    print("[Celery] Checking time-based reminders...")
