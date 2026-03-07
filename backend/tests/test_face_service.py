from app.services.face_service import compare_embeddings, generate_face_embedding, match_face_against_known


def test_embedding_is_deterministic_for_same_bytes() -> None:
    data = b"same-image-bytes"
    a = generate_face_embedding(data)
    b = generate_face_embedding(data)
    assert a == b
    assert len(a) == 128


def test_compare_embeddings_accepts_identical_vectors() -> None:
    emb = generate_face_embedding(b"abc")
    assert compare_embeddings(emb, emb, threshold=0.99)


def test_match_face_returns_best_known_person() -> None:
    alice = generate_face_embedding(b"alice-photo")
    bob = generate_face_embedding(b"bob-photo")

    matched = match_face_against_known(
        frame_embedding=alice,
        known_people=[
            {"id": "1", "name": "Bob", "face_embeddings": [bob]},
            {"id": "2", "name": "Alice", "face_embeddings": [alice]},
        ],
    )

    assert matched is not None
    assert matched["name"] == "Alice"
