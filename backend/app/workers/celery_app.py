from datetime import datetime, timezone

from celery import Celery
from celery.schedules import crontab
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import DATABASE_URL, REDIS_URL
from app.models.db import Event, Reminder

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


def _sync_db_url(async_url: str) -> str:
    if "+asyncpg" in async_url:
        return async_url.replace("+asyncpg", "+psycopg2")
    return async_url


@celery.task
def check_reminders():
    """
    Periodic task that scans active time reminders and logs reminder_triggered events.
    """
    now = datetime.now(timezone.utc)
    now_hhmm = now.strftime("%H:%M")
    engine = create_engine(_sync_db_url(DATABASE_URL), future=True)

    created_events = 0
    try:
        with Session(engine) as session:
            reminders = session.execute(
                select(Reminder).where(
                    Reminder.active.is_(True),
                    Reminder.type == "time",
                )
            ).scalars().all()

            for reminder in reminders:
                meta = reminder.trigger_meta or {}
                if meta.get("time") != now_hhmm:
                    continue

                event = Event(
                    patient_id=reminder.patient_id,
                    type="reminder_triggered",
                    payload={
                        "reminder_id": str(reminder.id),
                        "message": reminder.message,
                        "trigger_type": "time",
                        "trigger_time": now_hhmm,
                        "source": "celery",
                    },
                )
                session.add(event)
                created_events += 1

            if created_events:
                session.commit()
    finally:
        engine.dispose()

    print(f"[Celery] Reminder scan complete at {now_hhmm} UTC; triggered={created_events}")
    return {"triggered": created_events, "at_utc": now.isoformat()}
