import io

import pytest

from app.services.face_service import (
    REAL_FR_AVAILABLE,
    _fallback_generate_embedding,
    compare_embeddings,
    generate_face_embedding,
    match_face_against_known,
    EMBEDDING_SIZE,
)


# ── Fallback embedding tests ────────────────────────────────

def test_fallback_is_deterministic() -> None:
    data = b"same-image-bytes"
    a = _fallback_generate_embedding(data)
    b = _fallback_generate_embedding(data)
    assert a == b
    assert len(a) == EMBEDDING_SIZE


def test_fallback_different_inputs_differ() -> None:
    a = _fallback_generate_embedding(b"alice")
    b = _fallback_generate_embedding(b"bob")
    assert a != b


def test_fallback_empty_bytes_returns_zeros() -> None:
    emb = _fallback_generate_embedding(b"")
    assert emb == [0.0] * EMBEDDING_SIZE


# ── Cosine similarity / matching tests ──────────────────────

def test_compare_identical_vectors() -> None:
    emb = _fallback_generate_embedding(b"test")
    assert compare_embeddings(emb, emb, threshold=0.99)


def test_compare_zero_vectors_returns_false() -> None:
    zeros = [0.0] * EMBEDDING_SIZE
    assert not compare_embeddings(zeros, zeros)


def test_compare_empty_returns_false() -> None:
    assert not compare_embeddings([], [])
    assert not compare_embeddings([1.0], [])


def _pad(vals: list[float]) -> list[float]:
    return vals + [0.0] * (EMBEDDING_SIZE - len(vals))


def test_match_returns_best_person() -> None:
    alice = _fallback_generate_embedding(b"alice-photo")
    bob = _fallback_generate_embedding(b"bob-photo")

    matched = match_face_against_known(
        frame_embedding=alice,
        known_people=[
            {"id": "1", "name": "Bob", "face_embeddings": [bob]},
            {"id": "2", "name": "Alice", "face_embeddings": [alice]},
        ],
    )
    assert matched is not None
    assert matched["name"] == "Alice"


def test_match_zero_embedding_returns_none() -> None:
    zeros = [0.0] * EMBEDDING_SIZE
    alice = _fallback_generate_embedding(b"alice")
    result = match_face_against_known(
        frame_embedding=zeros,
        known_people=[{"id": "1", "name": "Alice", "face_embeddings": [alice]}],
    )
    assert result is None


def test_match_no_known_people_returns_none() -> None:
    emb = _fallback_generate_embedding(b"someone")
    assert match_face_against_known(emb, []) is None


def test_match_prefers_candidate_that_passes_all_gates() -> None:
    frame = _pad([1.0, 0.0])
    high_cosine_but_far = _pad([100.0, 1.0])  # would fail distance gate
    valid_match = _pad([0.95, 0.2])  # passes both cosine and distance gates

    matched = match_face_against_known(
        frame_embedding=frame,
        known_people=[
            {
                "id": "1",
                "name": "Alice",
                "face_embeddings": [high_cosine_but_far, valid_match],
            }
        ],
    )
    assert matched is not None
    assert matched["name"] == "Alice"


def test_match_rejects_when_only_far_candidates() -> None:
    frame = _pad([1.0, 0.0])
    too_far = _pad([2.0, 0.0])  # cosine high, Euclidean distance 1.0
    matched = match_face_against_known(
        frame_embedding=frame,
        known_people=[{"id": "1", "name": "Alice", "face_embeddings": [too_far]}],
    )
    assert matched is None


@pytest.mark.skipif(not REAL_FR_AVAILABLE, reason="face_recognition not installed")
def test_real_fr_no_face_image_returns_zero_embedding() -> None:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (128, 128), (255, 255, 255)).save(buf, format="JPEG")
    emb = generate_face_embedding(buf.getvalue())

    assert len(emb) == EMBEDDING_SIZE
    assert all(abs(v) < 1e-12 for v in emb)
