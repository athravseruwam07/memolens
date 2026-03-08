from dataclasses import dataclass
from datetime import datetime, timedelta

from app.services.object_service import (
    ITEM_WRITE_COOLDOWN_SECONDS,
    MIN_CONFIDENCE_DELTA,
    extract_item_detections,
    merge_detections,
    resolve_item_room,
    should_write_item_update,
)


def test_extract_item_detections_filters_by_tracked_items() -> None:
    payload = {
        "detections": [
            {"item": "keys", "room": "kitchen", "confidence": 0.88},
            {"item": "phone", "room": "hall", "confidence": 0.91},
            {"item": "book", "room": "desk", "confidence": 0.99},
        ]
    }

    out = extract_item_detections(payload=payload, tracked_items=["keys", "phone"])
    names = {d["item_name"] for d in out}

    assert names == {"keys", "phone"}


def test_extract_item_detections_maps_requested_classes() -> None:
    payload = {
        "detections": [
            {"item": "mouse", "confidence": 0.81},
            {"item": "wallet", "confidence": 0.77},
            {"item": "laptop", "confidence": 0.9},
            {"item": "shoe", "confidence": 0.8},
            {"item": "eyeglasses", "confidence": 0.86},
            {"item": "medicine bottle", "confidence": 0.74},
        ]
    }

    out = extract_item_detections(
        payload=payload,
        tracked_items=["computer mouse", "wallet", "laptop", "shoes", "glasses", "medicine"],
    )
    names = {d["item_name"] for d in out}
    assert names == {"computer mouse", "wallet", "laptop", "shoes", "glasses", "medication"}


def test_merge_detections_prefers_higher_confidence() -> None:
    merged = merge_detections(
        [{"item_name": "keys", "room": "kitchen", "confidence": 0.4}],
        [{"item_name": "keys", "room": "living", "confidence": 0.9}],
    )

    assert len(merged) == 1
    assert merged[0]["room"] == "living"
    assert merged[0]["confidence"] == 0.9


def test_resolve_item_room_prefers_detection_room() -> None:
    room = resolve_item_room(
        detection={"item_name": "keys", "room": "Kitchen"},
        payload={"room": "hall"},
    )
    assert room == "kitchen"


def test_resolve_item_room_falls_back_to_payload_room() -> None:
    room = resolve_item_room(
        detection={"item_name": "keys"},
        payload={"room_label": "Living Room"},
    )
    assert room == "living room"


def test_resolve_item_room_returns_none_when_unknown() -> None:
    room = resolve_item_room(
        detection={"item_name": "keys"},
        payload={},
    )
    assert room is None


@dataclass
class _State:
    last_seen_room: str | None
    last_seen_at: datetime | None
    snapshot_url: str | None
    confidence: float | None


def test_should_write_item_update_for_new_state() -> None:
    now = datetime.utcnow()
    assert should_write_item_update(None, resolved_room="kitchen", confidence=0.8, now=now)


def test_should_write_item_update_when_room_changes() -> None:
    now = datetime.utcnow()
    state = _State(last_seen_room="hall", last_seen_at=now, snapshot_url="/x.jpg", confidence=0.7)
    assert should_write_item_update(state, resolved_room="kitchen", confidence=0.7, now=now)


def test_should_write_item_update_when_confidence_improves() -> None:
    now = datetime.utcnow()
    state = _State(last_seen_room="kitchen", last_seen_at=now, snapshot_url="/x.jpg", confidence=0.7)
    improved = 0.7 + MIN_CONFIDENCE_DELTA + 0.01
    assert should_write_item_update(state, resolved_room="kitchen", confidence=improved, now=now)


def test_should_write_item_update_when_snapshot_missing() -> None:
    now = datetime.utcnow()
    state = _State(last_seen_room="kitchen", last_seen_at=now, snapshot_url=None, confidence=0.7)
    assert should_write_item_update(state, resolved_room="kitchen", confidence=0.7, now=now)


def test_should_write_item_update_when_cooldown_elapsed() -> None:
    now = datetime.utcnow()
    last_seen = now - timedelta(seconds=ITEM_WRITE_COOLDOWN_SECONDS + 1)
    state = _State(last_seen_room="kitchen", last_seen_at=last_seen, snapshot_url="/x.jpg", confidence=0.7)
    assert should_write_item_update(state, resolved_room="kitchen", confidence=0.7, now=now)


def test_should_write_item_update_suppresses_unchanged_within_cooldown() -> None:
    now = datetime.utcnow()
    last_seen = now - timedelta(seconds=max(1, ITEM_WRITE_COOLDOWN_SECONDS - 1))
    state = _State(last_seen_room="kitchen", last_seen_at=last_seen, snapshot_url="/x.jpg", confidence=0.7)
    assert not should_write_item_update(state, resolved_room="kitchen", confidence=0.72, now=now)
