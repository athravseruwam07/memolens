from __future__ import annotations

import base64
from pathlib import Path


def read_image_bytes(path: str) -> bytes:
    return Path(path).read_bytes()


def encode_b64(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8")


def decode_b64(data: str) -> bytes:
    return base64.b64decode(data)
