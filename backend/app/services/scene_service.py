"""
Scene/Room classification service for MemoLens.
Uses a pre-trained model to classify camera frames into room types.
"""

from __future__ import annotations

import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Room categories we care about for dementia support
ROOM_CATEGORIES = [
    "kitchen",
    "bedroom", 
    "bathroom",
    "living_room",
    "dining_room",
    "office",
    "hallway",
    "entrance",
    "garage",
    "laundry_room",
]

# Mapping from Places365 categories to our simplified room names
PLACES365_TO_ROOM = {
    # Kitchen
    "kitchen": "kitchen",
    "kitchenette": "kitchen",
    "galley": "kitchen",
    
    # Bedroom
    "bedroom": "bedroom",
    "hotel_room": "bedroom",
    "youth_hostel": "bedroom",
    "dorm_room": "bedroom",
    "nursery": "bedroom",
    "childs_room": "bedroom",
    
    # Bathroom
    "bathroom": "bathroom",
    "shower": "bathroom",
    "toilet": "bathroom",
    "locker_room": "bathroom",
    
    # Living room
    "living_room": "living_room",
    "television_room": "living_room",
    "home_theater": "living_room",
    "recreation_room": "living_room",
    "playroom": "living_room",
    
    # Dining room
    "dining_room": "dining_room",
    "banquet_hall": "dining_room",
    "cafeteria": "dining_room",
    
    # Office
    "office": "office",
    "home_office": "office",
    "computer_room": "office",
    "cubicle": "office",
    "study": "office",
    "library": "office",
    
    # Hallway
    "hallway": "hallway",
    "corridor": "hallway",
    "staircase": "hallway",
    "elevator_lobby": "hallway",
    
    # Entrance
    "entrance_hall": "entrance",
    "lobby": "entrance",
    "doorway": "entrance",
    "porch": "entrance",
    "vestibule": "entrance",
    
    # Garage
    "garage": "garage",
    "parking_garage": "garage",
    "carport": "garage",
    
    # Laundry
    "laundromat": "laundry_room",
    "utility_room": "laundry_room",
}

# Model state
_SCENE_MODEL = None
_SCENE_TRANSFORM = None
_SCENE_LABELS = None
_SCENE_INIT_ATTEMPTED = False


def _load_scene_model():
    """
    Load the scene classification model.
    Uses torchvision's pretrained ResNet18 with Places365 weights if available,
    otherwise falls back to ImageNet-pretrained model with heuristic mapping.
    """
    global _SCENE_MODEL, _SCENE_TRANSFORM, _SCENE_LABELS, _SCENE_INIT_ATTEMPTED
    
    if _SCENE_INIT_ATTEMPTED:
        return _SCENE_MODEL
    
    _SCENE_INIT_ATTEMPTED = True
    
    try:
        import torch
        import torchvision.transforms as transforms
        from torchvision import models
    except ImportError:
        logger.warning("PyTorch/torchvision not available - scene classification disabled")
        return None
    
    try:
        # Try to load Places365-trained model
        # Using ResNet18 as base - lightweight and fast
        model = models.resnet18(weights=None)
        
        # Check for custom Places365 weights
        import os
        weights_path = os.path.join(
            os.path.dirname(__file__), 
            "..", "..", "models", "scene_resnet18_places365.pth"
        )
        
        if os.path.exists(weights_path):
            # Load Places365 weights
            model.fc = torch.nn.Linear(model.fc.in_features, 365)
            state_dict = torch.load(weights_path, map_location="cpu")
            model.load_state_dict(state_dict)
            logger.info("Loaded Places365 scene model")
            
            # Load Places365 labels
            labels_path = os.path.join(
                os.path.dirname(__file__),
                "..", "..", "models", "places365_categories.txt"
            )
            if os.path.exists(labels_path):
                with open(labels_path, "r") as f:
                    _SCENE_LABELS = [line.strip().split(" ")[0].replace("/", "_") for line in f]
            else:
                _SCENE_LABELS = None
        else:
            # Fallback: Use ImageNet pretrained model
            # This won't be as accurate for rooms but provides basic scene understanding
            model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
            logger.info("Using ImageNet pretrained model for scene classification (Places365 weights not found)")
            _SCENE_LABELS = None
        
        model.eval()
        _SCENE_MODEL = model
        
        # Standard ImageNet/Places normalization
        _SCENE_TRANSFORM = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            ),
        ])
        
        return _SCENE_MODEL
        
    except Exception as e:
        logger.error(f"Failed to load scene model: {e}")
        _SCENE_MODEL = None
        return None


def _classify_with_places365(img_tensor) -> tuple[str | None, float]:
    """Classify using Places365-trained model."""
    import torch
    
    with torch.no_grad():
        outputs = _SCENE_MODEL(img_tensor)
        probabilities = torch.nn.functional.softmax(outputs, dim=1)
        
        # Get top predictions
        top_probs, top_indices = torch.topk(probabilities, 5)
        
        # Find best matching room category
        for i, (prob, idx) in enumerate(zip(top_probs[0], top_indices[0])):
            if _SCENE_LABELS and idx.item() < len(_SCENE_LABELS):
                label = _SCENE_LABELS[idx.item()]
                room = PLACES365_TO_ROOM.get(label)
                if room:
                    return room, float(prob.item())
        
        # No match found in our room categories
        return None, 0.0


def _classify_with_imagenet_heuristics(img_tensor) -> tuple[str | None, float]:
    """
    Fallback classification using ImageNet model with object-based heuristics.
    Detects common room-indicating objects to infer room type.
    """
    import torch
    
    # ImageNet class indices for room-indicating objects
    # See: https://gist.github.com/yrevar/942d3a0ac09ec9e5eb3a
    IMAGENET_ROOM_HINTS = {
        # Kitchen indicators
        "kitchen": [
            567,  # frying pan
            504,  # coffeepot
            659,  # mixing bowl
            923,  # plate
            968,  # cup
            550,  # espresso maker
            766,  # refrigerator
            827,  # stove
            879,  # toaster
            858,  # teapot
        ],
        # Bedroom indicators
        "bedroom": [
            560,  # folding chair
            831,  # studio couch
            759,  # pillow
            950,  # cradle
            598,  # hammock (relaxation)
        ],
        # Bathroom indicators
        "bathroom": [
            906,  # washbasin
            861,  # toilet seat
            878,  # tub/bathtub
            830,  # shower curtain
            859,  # hand towel (custom, may not exist)
        ],
        # Living room indicators
        "living_room": [
            831,  # studio couch
            892,  # wall clock
            851,  # television/monitor
            764,  # remote control
            809,  # rocking chair
            559,  # folding chair
            765,  # recliner (may overlap)
        ],
        # Office indicators
        "office": [
            527,  # desktop computer
            664,  # mouse (computer)
            508,  # computer keyboard
            681,  # notebook/laptop
            620,  # file cabinet (common)
            782,  # monitor
            742,  # printer
        ],
    }
    
    with torch.no_grad():
        outputs = _SCENE_MODEL(img_tensor)
        probabilities = torch.nn.functional.softmax(outputs, dim=1)[0]
        
        # Get top-5 predictions for logging
        top_probs, top_indices = torch.topk(probabilities, 5)
        
        # Score each room based on detected object probabilities
        room_scores = {}
        for room, indices in IMAGENET_ROOM_HINTS.items():
            score = sum(float(probabilities[idx].item()) for idx in indices if idx < len(probabilities))
            room_scores[room] = score
        
        # Get best room
        best_room = max(room_scores, key=room_scores.get)
        best_score = room_scores[best_room]
        
        # Lower threshold for returning a room guess (0.02 instead of 0.05)
        # This is more lenient since ImageNet isn't trained for scene classification
        if best_score > 0.02:
            confidence = min(best_score * 3, 0.85)  # Scale up but cap
            logger.debug(f"Scene classified as {best_room} with confidence {confidence:.3f}")
            return best_room, confidence
        
        return None, 0.0


def classify_scene(frame_bytes: bytes) -> tuple[str | None, float]:
    """
    Classify the scene/room from frame bytes.
    
    Args:
        frame_bytes: JPEG or PNG image bytes
        
    Returns:
        Tuple of (room_name, confidence) or (None, 0.0) if classification fails
    """
    model = _load_scene_model()
    if model is None:
        return None, 0.0
    
    try:
        from PIL import Image
        import torch
    except ImportError:
        return None, 0.0
    
    try:
        # Decode image
        img = Image.open(io.BytesIO(frame_bytes)).convert("RGB")
        
        # Transform for model
        img_tensor = _SCENE_TRANSFORM(img).unsqueeze(0)
        
        # Classify based on available model
        if _SCENE_LABELS:
            return _classify_with_places365(img_tensor)
        else:
            return _classify_with_imagenet_heuristics(img_tensor)
            
    except Exception as e:
        logger.error(f"Scene classification failed: {e}")
        return None, 0.0


def get_room_display_name(room: str | None) -> str:
    """Convert internal room name to display-friendly name."""
    if not room:
        return "unknown location"
    
    display_names = {
        "kitchen": "kitchen",
        "bedroom": "bedroom",
        "bathroom": "bathroom",
        "living_room": "living room",
        "dining_room": "dining room",
        "office": "office",
        "hallway": "hallway",
        "entrance": "entrance",
        "garage": "garage",
        "laundry_room": "laundry room",
    }
    return display_names.get(room, room.replace("_", " "))
