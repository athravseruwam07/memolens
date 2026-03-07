import pytest
from fastapi import HTTPException

from app.dependencies import ensure_patient_access


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeDB:
    def __init__(self, value):
        self._value = value

    async def execute(self, _stmt):
        return _FakeResult(self._value)


class _FakeUser:
    def __init__(self, user_id):
        self.id = user_id


@pytest.mark.asyncio
async def test_ensure_patient_access_allows_linked_user() -> None:
    db = _FakeDB(value=object())
    user = _FakeUser(user_id="u1")

    await ensure_patient_access(db=db, user=user, patient_id="p1")


@pytest.mark.asyncio
async def test_ensure_patient_access_denies_unlinked_user() -> None:
    db = _FakeDB(value=None)
    user = _FakeUser(user_id="u1")

    with pytest.raises(HTTPException) as exc:
        await ensure_patient_access(db=db, user=user, patient_id="p1")

    assert exc.value.status_code == 403
