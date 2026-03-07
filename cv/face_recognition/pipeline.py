from __future__ import annotations

import hashlib
from typing import Iterable


def deterministic_embedding(image_bytes: bytes, dim: int = 128) -> list[float]:
    if not image_bytes:
        return [0.0] * dim
    digest = hashlib.sha256(image_bytes).digest()
    vec = [((digest[i % len(digest)] / 255.0) * 2.0) - 1.0 for i in range(dim)]
    norm = sum(v * v for v in vec) ** 0.5
    if norm == 0:
        return [0.0] * dim
    return [v / norm for v in vec]


def cosine_similarity(a: Iterable[float], b: Iterable[float]) -> float:
    av = list(a)
    bv = list(b)
    dot = sum(x * y for x, y in zip(av, bv))
    na = sum(x * x for x in av) ** 0.5
    nb = sum(y * y for y in bv) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
