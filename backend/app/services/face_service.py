"""
Face embedding helpers.
Uses the face_recognition library for real face detection and encoding,
with a deterministic fallback when the library is unavailable.
"""

from __future__ import annotations

import hashlib
import io
import logging
import math
from typing import Sequence

import numpy as np

logger = logging.getLogger(__name__)

try:
    import face_recognition as _fr
    REAL_FR_AVAILABLE = True
    logger.info("face_recognition library loaded — real face recognition enabled")
except ImportError:
    _fr = None  # type: ignore[assignment]
    REAL_FR_AVAILABLE = False
    logger.warning(
        "face_recognition not installed — using deterministic fallback. "
        "Install with: pip install face_recognition"
    )

EMBEDDING_SIZE = 128
MATCH_THRESHOLD = 0.6
FACE_DISTANCE_THRESHOLD = 0.6


# -- Real implementation --------------------------------------------------------

def _face_area(loc: tuple[int, int, int, int]) -> int:
    """Return pixel area of a face bounding box (top, right, bottom, left)."""
    return abs(loc[2] - loc[0]) * abs(loc[3] - loc[1])


def _real_generate_embedding(image_bytes: bytes) -> list[float] | None:
    """Decode JPEG bytes, detect faces, encode the largest face."""
    from PIL import Image

    img_pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img_array = np.array(img_pil)

    face_locations = _fr.face_locations(img_array, model="hog")
    if not face_locations:
        return None

    # Multiple faces → pick the largest bounding box
    best_loc = max(face_locations, key=_face_area)

    encodings = _fr.face_encodings(img_array, known_face_locations=[best_loc])
    if not encodings:
        return None

    return encodings[0].tolist()


# -- Deterministic fallback -----------------------------------------------------

def _fallback_generate_embedding(image_bytes: bytes) -> list[float]:
    """Original SHA256 + byte-statistics deterministic embedding."""
    if not image_bytes:
        return [0.0] * EMBEDDING_SIZE

    chunk_size = max(1, len(image_bytes) // EMBEDDING_SIZE)
    stats_vec: list[float] = []
    for idx in range(EMBEDDING_SIZE):
        start = idx * chunk_size
        end = min(len(image_bytes), start + chunk_size)
        chunk = image_bytes[start:end] or image_bytes[-chunk_size:]
        mean_byte = sum(chunk) / (len(chunk) * 255.0)
        stats_vec.append((mean_byte * 2.0) - 1.0)

    digest = hashlib.sha256(image_bytes).digest()
    digest_vec = [((digest[i % len(digest)] / 255.0) * 2.0) - 1.0 for i in range(EMBEDDING_SIZE)]
    combined = [(0.7 * a) + (0.3 * b) for a, b in zip(stats_vec, digest_vec)]
    norm = math.sqrt(sum(v * v for v in combined))
    if norm == 0:
        return [0.0] * EMBEDDING_SIZE
    return [v / norm for v in combined]


# -- Public API -----------------------------------------------------------------


def _is_valid_embedding(embedding: Sequence[float] | None) -> bool:
    """Ensure embeddings are fixed-size numeric vectors before matching."""
    return bool(embedding) and len(embedding) == EMBEDDING_SIZE


def generate_face_embedding(image_bytes: bytes) -> list[float]:
    """
    Generate a 128-d face embedding from raw image bytes (JPEG/PNG).
    Returns a zero vector if no face is detected.
    """
    if REAL_FR_AVAILABLE:
        try:
            result = _real_generate_embedding(image_bytes)
            if result is not None:
                return result
            return [0.0] * EMBEDDING_SIZE
        except Exception:
            # Avoid silently generating incompatible fake vectors on runtime failures.
            logger.exception("face_recognition failed while encoding image")
            return [0.0] * EMBEDDING_SIZE
    return _fallback_generate_embedding(image_bytes)


def compare_embeddings(
    embedding_a: list[float],
    embedding_b: list[float],
    threshold: float = MATCH_THRESHOLD,
) -> bool:
    """Compare two 128-d embeddings using cosine similarity."""
    if not _is_valid_embedding(embedding_a) or not _is_valid_embedding(embedding_b):
        return False
    dot = sum(a * b for a, b in zip(embedding_a, embedding_b))
    norm_a = sum(a ** 2 for a in embedding_a) ** 0.5
    norm_b = sum(b ** 2 for b in embedding_b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return False
    similarity = dot / (norm_a * norm_b)
    return similarity >= threshold


def match_face_against_known(
    frame_embedding: list[float],
    known_people: list[dict],
    threshold: float = MATCH_THRESHOLD,
) -> dict | None:
    """
    Match a face embedding against known people's stored embeddings.
    Returns the best matching person dict or None.
    """
    if not _is_valid_embedding(frame_embedding):
        return None

    # Skip zero vectors (no face detected)
    norm_frame = sum(a ** 2 for a in frame_embedding) ** 0.5
    if norm_frame == 0:
        return None

    best_person = None
    best_score = float("-inf")
    best_distance = float("inf")

    for person in known_people:
        embeddings = person.get("face_embeddings") or []
        for stored in embeddings:
            if not _is_valid_embedding(stored):
                continue
            dot = sum(a * b for a, b in zip(frame_embedding, stored))
            norm_b = sum(b ** 2 for b in stored) ** 0.5
            if norm_b == 0:
                continue
            similarity = dot / (norm_frame * norm_b)
            # Also compute Euclidean distance (face_recognition standard metric)
            euclidean = math.sqrt(sum((a - b) ** 2 for a, b in zip(frame_embedding, stored)))

            if similarity < threshold:
                continue
            if euclidean > FACE_DISTANCE_THRESHOLD:
                continue

            if similarity > best_score or (
                math.isclose(similarity, best_score) and euclidean < best_distance
            ):
                best_score = similarity
                best_distance = euclidean
                best_person = person

    if best_person:
        return best_person

    return None
