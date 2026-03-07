"""
Face embedding helpers.
This implementation is deterministic (same image bytes => same embedding), which
allows reliable matching in demos even when heavy CV dependencies are unavailable.
"""

from __future__ import annotations

import hashlib
import math


EMBEDDING_SIZE = 128


def _chunked_embedding(image_bytes: bytes) -> list[float]:
    if not image_bytes:
        return [0.0] * EMBEDDING_SIZE

    chunk_size = max(1, len(image_bytes) // EMBEDDING_SIZE)
    values: list[float] = []
    for idx in range(EMBEDDING_SIZE):
        start = idx * chunk_size
        end = min(len(image_bytes), start + chunk_size)
        chunk = image_bytes[start:end] or image_bytes[-chunk_size:]
        mean_byte = sum(chunk) / (len(chunk) * 255.0)
        values.append((mean_byte * 2.0) - 1.0)
    return values


def generate_face_embedding(image_bytes: bytes) -> list[float]:
    """
    Generate a deterministic 128-d embedding from image bytes.
    Uses both chunk statistics and SHA-256 digest so near-identical images
    remain close while exact images match strongly.
    """
    stats_vec = _chunked_embedding(image_bytes)
    digest = hashlib.sha256(image_bytes).digest()
    digest_vec = [((digest[i % len(digest)] / 255.0) * 2.0) - 1.0 for i in range(EMBEDDING_SIZE)]
    # Blend both signals and normalize.
    combined = [(0.7 * a) + (0.3 * b) for a, b in zip(stats_vec, digest_vec)]
    norm = math.sqrt(sum(v * v for v in combined))
    if norm == 0:
        return [0.0] * EMBEDDING_SIZE
    return [v / norm for v in combined]


def compare_embeddings(embedding_a: list[float], embedding_b: list[float], threshold: float = 0.90) -> bool:
    """Compare two 128-d embeddings using cosine similarity. Returns True if match."""
    if not embedding_a or not embedding_b:
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
) -> dict | None:
    """
    Match a face embedding against known people's stored embeddings.
    known_people: list of { "id", "name", "relationship", "notes", "face_embeddings": [[...], ...] }
    Returns the best matching person dict or None.
    """
    best_person = None
    best_score = -1.0

    for person in known_people:
        embeddings = person.get("face_embeddings") or []
        for stored in embeddings:
            if not frame_embedding or not stored:
                continue
            dot = sum(a * b for a, b in zip(frame_embedding, stored))
            norm_a = sum(a ** 2 for a in frame_embedding) ** 0.5
            norm_b = sum(b ** 2 for b in stored) ** 0.5
            if norm_a == 0 or norm_b == 0:
                continue
            similarity = dot / (norm_a * norm_b)
            if similarity > best_score:
                best_score = similarity
                best_person = person

    if best_person and best_score >= 0.90:
        return best_person
    return None
