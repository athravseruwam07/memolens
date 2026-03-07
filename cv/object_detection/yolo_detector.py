from __future__ import annotations

import argparse
from pathlib import Path


def detect_items(image_path: str, tracked_items: set[str]) -> list[dict]:
    try:
        from ultralytics import YOLO
    except Exception:
        return []

    model = YOLO("yolov8n.pt")
    result = model(image_path, verbose=False)
    if not result:
        return []

    map_labels = {
        "cell phone": "phone",
        "remote": "remote",
        "bottle": "medication",
        "book": "book"
    }

    detections: list[dict] = []
    for box in result[0].boxes:
        label = model.names[int(box.cls)]
        item = map_labels.get(label, label)
        if tracked_items and item not in tracked_items:
            continue
        conf = float(box.conf.item()) if hasattr(box.conf, "item") else float(box.conf)
        detections.append({"item": item, "confidence": conf, "room": None})
    return detections


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--tracked-items", default="")
    args = parser.parse_args()

    image = Path(args.image)
    if not image.exists():
        raise SystemExit(f"Image not found: {image}")

    tracked = {i.strip().lower() for i in args.tracked_items.split(",") if i.strip()}
    detections = detect_items(str(image), tracked)
    print(detections)


if __name__ == "__main__":
    main()
