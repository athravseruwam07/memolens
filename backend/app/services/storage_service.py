from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path
from urllib.parse import quote

import httpx

from app.config import (
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY,
    SUPABASE_STORAGE_BUCKET,
    LOCAL_UPLOAD_DIR,
)


def _safe_suffix(filename: str | None) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        return suffix
    return ".jpg"


def _public_url_for_object(object_path: str) -> str:
    encoded_path = quote(object_path, safe="/")
    return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_STORAGE_BUCKET}/{encoded_path}"


async def _upload_to_supabase(object_path: str, content: bytes, content_type: str) -> str | None:
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return None

    url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_STORAGE_BUCKET}/{object_path}"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "x-upsert": "true",
        "content-type": content_type,
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        res = await client.post(url, headers=headers, content=content)
    if 200 <= res.status_code < 300:
        return _public_url_for_object(object_path)
    return None


def _store_locally(object_path: str, content: bytes) -> str:
    base = Path(LOCAL_UPLOAD_DIR)
    target = base / object_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return f"/uploads/{object_path}"


async def upload_person_photo(
    *,
    patient_id: str,
    person_id: str,
    filename: str | None,
    content: bytes,
) -> str:
    suffix = _safe_suffix(filename)
    object_path = f"patients/{patient_id}/people/{person_id}/{uuid.uuid4().hex}{suffix}"
    content_type = mimetypes.guess_type(f"file{suffix}")[0] or "application/octet-stream"

    supabase_url = await _upload_to_supabase(object_path=object_path, content=content, content_type=content_type)
    if supabase_url:
        return supabase_url

    return _store_locally(object_path=object_path, content=content)


async def upload_item_snapshot(
    *,
    patient_id: str,
    item_name: str,
    content: bytes,
) -> str:
    safe_item = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in item_name.lower())
    object_path = f"patients/{patient_id}/items/{safe_item}/{uuid.uuid4().hex}.jpg"
    content_type = "image/jpeg"

    supabase_url = await _upload_to_supabase(object_path=object_path, content=content, content_type=content_type)
    if supabase_url:
        return supabase_url

    return _store_locally(object_path=object_path, content=content)
