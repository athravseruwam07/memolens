"""
Face recognition service stub.
In production, this would use a real face embedding model (e.g. dlib, FaceNet).
For the hackathon demo, this provides placeholder implementations.
"""

import random


def generate_face_embedding(image_bytes: bytes) -> list[float]:
    """Generate a 128-d face embedding from image bytes. Stub: returns random vector."""
    return [random.uniform(-1, 1) for _ in range(128)]


def compare_embeddings(embedding_a: list[float], embedding_b: list[float], threshold: float = 0.6) -> bool:
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
    for person in known_people:
        embeddings = person.get("face_embeddings") or []
        for stored in embeddings:
            if compare_embeddings(frame_embedding, stored):
                return person
    return None
