"""
Zero-Shot Object Detection Service for MemoLens.

Uses YOLO-World for open-vocabulary object detection, allowing detection
of ANY object specified by text (e.g., "water bottle", "airpods", "keys").

Falls back to standard YOLOv8 COCO detection if YOLO-World is unavailable.

Configuration:
    Set DETECTION_MODE environment variable:
    - "zeroshot" (default): Use YOLO-World for custom classes
    - "coco": Use standard YOLOv8 with COCO classes only
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Detection mode: "zeroshot" or "coco"
DETECTION_MODE = os.environ.get("DETECTION_MODE", "zeroshot").lower()

# Comprehensive list of items to detect with zero-shot detection
# These are the classes YOLO-World will look for in every frame
# Add/remove items as needed - YOLO-World can detect ANY of these!
ZEROSHOT_CLASSES = [
    # === High Priority - Common items dementia patients lose ===
    "keys", "key", "car key", "house key", "keychain",
    "wallet", "purse", "handbag", "money clip",
    "phone", "cell phone", "smartphone", "mobile phone", "iphone",
    "glasses", "eyeglasses", "reading glasses", "sunglasses", "spectacles",
    "hearing aid", "hearing aids",
    "watch", "wristwatch", "smart watch",
    "remote", "tv remote", "remote control",
    "medication", "medicine", "pill bottle", "pills", "medicine bottle",
    "dentures", "false teeth",
    "cane", "walking stick", "walker", "walking frame",
    
    # === Electronics ===
    "laptop", "computer", "tablet", "ipad",
    "charger", "phone charger", "charging cable",
    "headphones", "earbuds", "airpods", "earphones",
    "mouse", "computer mouse", "keyboard",
    "television", "tv", "monitor",
    
    # === Personal Items ===
    "ring", "wedding ring", "jewelry", "bracelet", "necklace",
    "hat", "cap", "scarf", "gloves",
    "coat", "jacket", "sweater", "cardigan",
    "shoes", "slippers", "sandals", "boots",
    "bag", "backpack", "tote bag", "shopping bag",
    "umbrella",
    
    # === Documents ===
    "passport", "id card", "driver license", "credit card", "debit card",
    "book", "notebook", "calendar", "newspaper", "magazine",
    "pen", "pencil",
    
    # === Kitchen Items ===
    "cup", "mug", "coffee cup", "tea cup",
    "bottle", "water bottle", "glass", "wine glass",
    "bowl", "plate", "fork", "knife", "spoon",
    
    # === Household Items ===
    "blanket", "pillow", "towel",
    "scissors", "tape", "flashlight",
    "toothbrush", "toothpaste", "razor", "comb", "brush",
    
    # === Furniture (for context) ===
    "chair", "couch", "sofa", "bed", "table", "desk",
]

# Model instances (lazy loaded)
_YOLOWORLD_MODEL = None
_YOLOWORLD_INIT_ATTEMPTED = False
_YOLO_COCO_MODEL = None
_YOLO_COCO_INIT_ATTEMPTED = False


def _load_yoloworld_model():
    """Load YOLO-World model for zero-shot detection."""
    global _YOLOWORLD_MODEL, _YOLOWORLD_INIT_ATTEMPTED
    
    if _YOLOWORLD_INIT_ATTEMPTED:
        return _YOLOWORLD_MODEL
    _YOLOWORLD_INIT_ATTEMPTED = True
    
    try:
        from ultralytics import YOLO
    except ImportError:
        logger.warning("Ultralytics not installed, zero-shot detection unavailable")
        return None
    
    # Try multiple YOLO-World model variants in order of preference
    model_options = [
        "yolov8s-worldv2.pt",  # Preferred: v2 small model
        "yolov8s-world.pt",    # Fallback: v1 small model  
        "yolov8n-worldv2.pt",  # Lighter: nano v2
        "yolov8n-world.pt",    # Lightest: nano v1
    ]
    
    for model_name in model_options:
        try:
            logger.info(f"Attempting to load YOLO-World: {model_name}")
            _YOLOWORLD_MODEL = YOLO(model_name)
            
            # Set the classes we want to detect
            _YOLOWORLD_MODEL.set_classes(ZEROSHOT_CLASSES)
            
            logger.info(f"YOLO-World loaded ({model_name}) with {len(ZEROSHOT_CLASSES)} custom classes")
            return _YOLOWORLD_MODEL
            
        except Exception as e:
            logger.warning(f"Failed to load {model_name}: {e}")
            continue
    
    logger.error("All YOLO-World model variants failed to load")
    _YOLOWORLD_MODEL = None
    return None


def _load_yolo_coco_model():
    """Load standard YOLOv8 COCO model as fallback."""
    global _YOLO_COCO_MODEL, _YOLO_COCO_INIT_ATTEMPTED
    
    if _YOLO_COCO_INIT_ATTEMPTED:
        return _YOLO_COCO_MODEL
    _YOLO_COCO_INIT_ATTEMPTED = True
    
    try:
        from ultralytics import YOLO
        _YOLO_COCO_MODEL = YOLO("yolov8n.pt")
        logger.info("Standard YOLOv8 COCO model loaded as fallback")
        return _YOLO_COCO_MODEL
    except Exception as e:
        logger.error(f"Failed to load YOLOv8 COCO: {e}")
        _YOLO_COCO_MODEL = None
        return None


def get_active_model():
    """Get the active detection model based on configuration."""
    if DETECTION_MODE == "zeroshot":
        model = _load_yoloworld_model()
        if model is not None:
            return model, "zeroshot"
        # Fallback to COCO
        logger.warning("YOLO-World unavailable, falling back to COCO detection")
    
    model = _load_yolo_coco_model()
    return model, "coco"


def detect_objects_zeroshot(
    frame_bytes: bytes,
    custom_classes: list[str] | None = None,
    confidence_threshold: float = 0.15,
) -> list[dict[str, Any]]:
    """
    Detect objects using zero-shot detection (YOLO-World).
    
    Args:
        frame_bytes: JPEG/PNG image bytes
        custom_classes: Optional list of specific classes to detect.
                       If None, uses ZEROSHOT_CLASSES.
        confidence_threshold: Minimum confidence to include detection
        
    Returns:
        List of detections with item_name, confidence, and bbox
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        logger.error("OpenCV not available")
        return []
    
    # Decode image
    nparr = np.frombuffer(frame_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None:
        return []
    
    model, mode = get_active_model()
    if model is None:
        return []
    
    # If custom classes provided and using YOLO-World, update classes
    if custom_classes and mode == "zeroshot":
        try:
            model.set_classes(custom_classes)
        except Exception as e:
            logger.warning(f"Could not set custom classes: {e}")
    
    # Run inference
    try:
        results = model(frame, verbose=False, conf=confidence_threshold)
    except Exception as e:
        logger.error(f"Detection failed: {e}")
        return []
    
    if not results or not results[0].boxes:
        return []
    
    detections = []
    for box in results[0].boxes:
        try:
            # Get class label
            cls_idx = int(box.cls.item() if hasattr(box.cls, "item") else box.cls)
            
            if mode == "zeroshot":
                # YOLO-World: classes are from our custom list
                if custom_classes:
                    label = custom_classes[cls_idx] if cls_idx < len(custom_classes) else str(cls_idx)
                else:
                    label = ZEROSHOT_CLASSES[cls_idx] if cls_idx < len(ZEROSHOT_CLASSES) else str(cls_idx)
            else:
                # COCO: use model's built-in names
                label = model.names.get(cls_idx, str(cls_idx))
            
            confidence = float(box.conf.item() if hasattr(box.conf, "item") else box.conf)
            
            # Get bounding box
            xyxy = box.xyxy[0].tolist() if hasattr(box.xyxy, "tolist") else list(box.xyxy[0])
            
            detections.append({
                "item_name": label.lower().strip(),
                "confidence": confidence,
                "bbox": xyxy,
                "detection_mode": mode,
            })
            
        except Exception as e:
            logger.warning(f"Error processing detection: {e}")
            continue
    
    # Sort by confidence (highest first)
    detections.sort(key=lambda x: x["confidence"], reverse=True)
    
    return detections


def detect_items_zeroshot(
    frame_bytes: bytes,
    tracked_items: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Main entry point for zero-shot item detection.
    Compatible with the existing detect_items_from_frame interface.
    
    Args:
        frame_bytes: Image bytes
        tracked_items: Optional list of specific items to track.
                      If None, detects all items in ZEROSHOT_CLASSES.
                      
    Returns:
        List of detections compatible with existing pipeline
    """
    # If specific items requested, use those; otherwise use full list
    classes_to_detect = None
    if tracked_items:
        # Combine tracked items with our default important items
        priority_items = [
            "keys", "wallet", "phone", "glasses", "watch", "remote",
            "medication", "hearing aid", "dentures", "cane",
        ]
        classes_to_detect = list(set(tracked_items + priority_items))
    
    # Higher confidence threshold (0.40) to reduce false positives
    detections = detect_objects_zeroshot(
        frame_bytes=frame_bytes,
        custom_classes=classes_to_detect,
        confidence_threshold=0.40,
    )
    
    # Normalize item names and filter
    from app.services.object_service import _normalize_item_name, _tracked_set
    
    tracked = _tracked_set(tracked_items) if tracked_items else set()
    
    results = []
    seen_items = set()
    
    for det in detections:
        item_name = _normalize_item_name(det["item_name"])
        if not item_name:
            continue
        
        # Skip if we're tracking specific items and this isn't one of them
        if tracked and item_name not in tracked:
            # But still include high-priority items
            priority = {"keys", "wallet", "phone", "glasses", "medication", "remote"}
            if item_name not in priority:
                continue
        
        # Skip duplicates (keep highest confidence)
        if item_name in seen_items:
            continue
        seen_items.add(item_name)
        
        results.append({
            "item_name": item_name,
            "room": None,
            "confidence": det["confidence"],
        })
    
    return results


def get_detection_info() -> dict[str, Any]:
    """Get information about the current detection configuration."""
    model, mode = get_active_model()
    
    return {
        "mode": mode,
        "configured_mode": DETECTION_MODE,
        "model_loaded": model is not None,
        "zeroshot_classes_count": len(ZEROSHOT_CLASSES),
        "zeroshot_available": _YOLOWORLD_MODEL is not None or not _YOLOWORLD_INIT_ATTEMPTED,
    }


# For easy testing
if __name__ == "__main__":
    import sys
    
    print("Zero-Shot Object Detection Test")
    print("=" * 50)
    
    info = get_detection_info()
    print(f"Detection mode: {info['mode']}")
    print(f"Classes available: {info['zeroshot_classes_count']}")
    
    if len(sys.argv) > 1:
        # Test with an image file
        image_path = sys.argv[1]
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        
        print(f"\nTesting with: {image_path}")
        detections = detect_objects_zeroshot(image_bytes)
        
        print(f"\nDetected {len(detections)} objects:")
        for det in detections[:10]:
            print(f"  - {det['item_name']}: {det['confidence']:.2%}")
