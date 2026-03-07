from app.services.object_service import extract_item_detections, merge_detections


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


def test_merge_detections_prefers_higher_confidence() -> None:
    merged = merge_detections(
        [{"item_name": "keys", "room": "kitchen", "confidence": 0.4}],
        [{"item_name": "keys", "room": "living", "confidence": 0.9}],
    )

    assert len(merged) == 1
    assert merged[0]["room"] == "living"
    assert merged[0]["confidence"] == 0.9
