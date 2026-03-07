from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.models.db import Reminder
from app.services import reminder_service


class _FakeResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return self

    def all(self):
        return list(self._items)


class _FakeDB:
    def __init__(self, reminders):
        self._reminders = reminders

    async def execute(self, _stmt):
        return _FakeResult(self._reminders)


def _mk_reminder(r_type: str, trigger_meta: dict):
    r = Reminder(
        id=uuid4(),
        patient_id=uuid4(),
        type=r_type,
        trigger_meta=trigger_meta,
        message="msg",
        active=True,
    )
    return r


async def _never_recently_triggered(*_args, **_kwargs):
    return False


@pytest.mark.asyncio
async def test_person_reminder_triggers_for_matching_person(monkeypatch):
    person_id = "person-123"
    reminders = [_mk_reminder("person", {"person_id": person_id, "cooldown_seconds": 0})]
    db = _FakeDB(reminders=reminders)

    monkeypatch.setattr(reminder_service, "_was_recently_triggered", _never_recently_triggered)

    out = await reminder_service.get_triggered_reminders(
        db,
        patient_id=uuid4(),
        person_id=person_id,
    )
    assert len(out) == 1


@pytest.mark.asyncio
async def test_location_reminder_triggers_for_room(monkeypatch):
    reminders = [_mk_reminder("location", {"room": "kitchen", "cooldown_seconds": 0})]
    db = _FakeDB(reminders=reminders)

    monkeypatch.setattr(reminder_service, "_was_recently_triggered", _never_recently_triggered)

    out = await reminder_service.get_triggered_reminders(
        db,
        patient_id=uuid4(),
        current_room="Kitchen",
    )
    assert len(out) == 1


@pytest.mark.asyncio
async def test_object_missing_before_exit_triggers(monkeypatch):
    reminders = [_mk_reminder("object", {"item": "keys", "mode": "missing_before_exit", "cooldown_seconds": 0})]
    db = _FakeDB(reminders=reminders)

    monkeypatch.setattr(reminder_service, "_was_recently_triggered", _never_recently_triggered)

    out = await reminder_service.get_triggered_reminders(
        db,
        patient_id=uuid4(),
        near_exit=True,
        detected_items={"phone"},
    )
    assert len(out) == 1


@pytest.mark.asyncio
async def test_time_reminder_triggers_for_current_hhmm(monkeypatch):
    now_hhmm = datetime.now(timezone.utc).strftime("%H:%M")
    reminders = [_mk_reminder("time", {"time": now_hhmm, "cooldown_seconds": 0})]
    db = _FakeDB(reminders=reminders)

    monkeypatch.setattr(reminder_service, "_was_recently_triggered", _never_recently_triggered)

    out = await reminder_service.get_triggered_reminders(
        db,
        patient_id=uuid4(),
    )
    assert len(out) == 1
