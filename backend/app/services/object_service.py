from __future__ import annotations

from datetime import datetime
from typing import Any


YOLO_LABEL_MAP = {
    "mouse": "computer mouse",
    "computer mouse": "computer mouse",
    "cell phone": "phone",
    "mobile phone": "phone",
    "wallet": "wallet",
    "purse": "wallet",
    "handbag": "wallet",
    "keys": "keys",
    "eyeglasses": "glasses",
    "glasses": "glasses",
    "laptop": "laptop",
    "tv remote": "remote",
    "remote control": "remote",
    "shoe": "shoes",
    "sneaker": "shoes",
    "boot": "shoes",
    "sandals": "shoes",
    "keychain": "keys",
    "house keys": "keys",
    "medicine": "medication",
    "medication": "medication",
    "pill bottle": "medication",
    "medicine bottle": "medication",
}
ROOM_KEYS = ("room", "room_label", "location")
ITEM_WRITE_COOLDOWN_SECONDS = 30
MIN_CONFIDENCE_DELTA = 0.05

_YOLO_MODEL = None
_YOLO_INIT_ATTEMPTED = False


def _normalize_item_name(name: str | None) -> str | None:
    if not name:
        return None
    n = name.strip().lower()
    return YOLO_LABEL_MAP.get(n, n)


def _tracked_set(tracked_items: list[str] | None) -> set[str]:
    return {_normalize_item_name(i) for i in (tracked_items or []) if _normalize_item_name(i)}


def _normalize_room_name(name: str | None) -> str | None:
    if not name:
        return None
    normalized = name.strip().lower()
    return normalized or None


def _load_yolo_model():
    global _YOLO_MODEL, _YOLO_INIT_ATTEMPTED
    if _YOLO_INIT_ATTEMPTED:
        return _YOLO_MODEL
    _YOLO_INIT_ATTEMPTED = True

    try:
        from ultralytics import YOLO  # type: ignore
    except Exception:
        return None

    try:
        _YOLO_MODEL = YOLO("yolov8n.pt")
    except Exception:
        _YOLO_MODEL = None
    return _YOLO_MODEL


def detect_items_from_frame(
    frame_bytes: bytes,
    tracked_items: list[str] | None,
) -> list[dict[str, Any]]:
    """
    Optional local YOLO detection path.
    Returns [] if required CV dependencies are unavailable.
    """
    model = _load_yolo_model()
    if model is None:
        return []

    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except Exception:
        return []

    nparr = np.frombuffer(frame_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None:
        return []

    tracked = _tracked_set(tracked_items)
    results = model(frame, verbose=False)
    out: list[dict[str, Any]] = []

    if not results:
        return out

    for box in results[0].boxes:
        label_idx = int(box.cls)
        raw_label = model.names.get(label_idx, str(label_idx))
        item_name = _normalize_item_name(raw_label)
        if not item_name:
            continue
        if tracked and item_name not in tracked:
            continue
        confidence = float(box.conf.item()) if hasattr(box.conf, "item") else float(box.conf)
        out.append(
            {
                "item_name": item_name,
                "room": None,
                "confidence": confidence,
            }
        )
    return out


def extract_item_detections(
    payload: dict[str, Any],
    tracked_items: list[str] | None,
) -> list[dict[str, Any]]:
    """
    Normalize item detections from stream payload.
    Expected payload shape:
      {
        "detections": [
          {"item": "keys", "room": "kitchen", "confidence": 0.88}
        ]
      }
    """
    tracked = _tracked_set(tracked_items)
    detections_raw = payload.get("detections") or []
    if not isinstance(detections_raw, list):
        return []

    out: list[dict[str, Any]] = []
    for d in detections_raw:
        if not isinstance(d, dict):
            continue
        raw_item = d.get("item") or d.get("name") or d.get("label")
        item_name = _normalize_item_name(raw_item)
        if not item_name:
            continue
        if tracked and item_name not in tracked:
            continue

        room = _normalize_room_name(d.get("room") or d.get("room_label") or d.get("location"))
        confidence = d.get("confidence")
        try:
            confidence = float(confidence) if confidence is not None else None
        except (TypeError, ValueError):
            confidence = None

        out.append(
            {
                "item_name": item_name,
                "room": room,
                "confidence": confidence,
            }
        )

    return out


def resolve_item_room(
    detection: dict[str, Any],
    payload: dict[str, Any] | None,
) -> str | None:
    """
    Resolve room with precedence:
    1) detection-level room keys
    2) payload-level room keys
    3) None
    """
    for source in (detection, payload or {}):
        for key in ROOM_KEYS:
            room = _normalize_room_name(source.get(key))
            if room:
                return room
    return None


def should_write_item_update(
    state: Any | None,
    *,
    resolved_room: str | None,
    confidence: float | None,
    now: datetime,
    cooldown_seconds: int = ITEM_WRITE_COOLDOWN_SECONDS,
    min_confidence_delta: float = MIN_CONFIDENCE_DELTA,
) -> bool:
    """
    Gate item writes and events to avoid per-frame churn.
    """
    if state is None:
        return True

    state_room = _normalize_room_name(getattr(state, "last_seen_room", None))
    if resolved_room != state_room:
        return True

    state_confidence = getattr(state, "confidence", None)
    if confidence is not None:
        if state_confidence is None:
            return True
        try:
            if confidence >= float(state_confidence) + float(min_confidence_delta):
                return True
        except (TypeError, ValueError):
            return True

    if not getattr(state, "snapshot_url", None):
        return True

    last_seen_at = getattr(state, "last_seen_at", None)
    if last_seen_at is None:
        return True

    try:
        return (now - last_seen_at).total_seconds() >= cooldown_seconds
    except Exception:
        return True


def merge_detections(*detection_sets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Merge detections by item_name, preferring entries with higher confidence.
    """
    merged: dict[str, dict[str, Any]] = {}
    for detections in detection_sets:
        for det in detections:
            item_name = det.get("item_name")
            if not item_name:
                continue
            current = merged.get(item_name)
            if current is None:
                merged[item_name] = det
                continue
            old_conf = current.get("confidence") if isinstance(current.get("confidence"), (float, int)) else -1.0
            new_conf = det.get("confidence") if isinstance(det.get("confidence"), (float, int)) else -1.0
            if new_conf > old_conf:
                merged[item_name] = det
    return list(merged.values())
