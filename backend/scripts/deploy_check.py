from __future__ import annotations

import argparse
import os
import re
import subprocess
from typing import Iterable

import httpx
from dotenv import load_dotenv


REQUIRED_BACKEND_ENV = [
    "DATABASE_URL",
    "REDIS_URL",
    "JWT_SECRET",
    "FRONTEND_URL",
    "FRONTEND_URLS",
]

OPTIONAL_BUT_RECOMMENDED = [
    "SUPABASE_URL",
    "SUPABASE_SERVICE_KEY",
    "SUPABASE_STORAGE_BUCKET",
]


def _check_env(required: Iterable[str], optional: Iterable[str]) -> tuple[list[str], list[str]]:
    missing_required = [k for k in required if not os.getenv(k)]
    missing_optional = [k for k in optional if not os.getenv(k)]
    return missing_required, missing_optional


def _extract_revision(text: str) -> str | None:
    m = re.search(r"([0-9a-f]{8,})", text)
    return m.group(1) if m else None


def _run(cmd: list[str]) -> str:
    out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
    return out.strip()


def _check_migrations() -> tuple[bool, str, str]:
    heads = _run(["alembic", "heads"])
    current = _run(["alembic", "current"])
    head_rev = _extract_revision(heads)
    current_rev = _extract_revision(current)
    ok = bool(head_rev and current_rev and head_rev == current_rev)
    return ok, heads, current


def _check_health(base_url: str) -> tuple[bool, str]:
    health_url = base_url.rstrip("/") + "/health"
    try:
        res = httpx.get(health_url, timeout=10.0)
        if res.status_code != 200:
            return False, f"HTTP {res.status_code}"
        payload = res.json()
        return payload.get("status") == "ok", str(payload)
    except Exception as exc:
        return False, str(exc)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate deployment env + migration state")
    parser.add_argument(
        "--backend-url",
        default="",
        help="Optional backend base URL for health check, e.g. https://memolens-backend.onrender.com",
    )
    parser.add_argument(
        "--skip-migration-check",
        action="store_true",
        help="Skip alembic current/head comparison",
    )
    return parser.parse_args()


def main() -> int:
    load_dotenv()
    args = parse_args()

    print("[1/3] Checking required environment variables...")
    missing_required, missing_optional = _check_env(REQUIRED_BACKEND_ENV, OPTIONAL_BUT_RECOMMENDED)
    if missing_required:
        print("Missing required env vars:")
        for k in missing_required:
            print(f"- {k}")
        return 1
    print("Required env vars: OK")

    if missing_optional:
        print("Optional vars missing (recommended for storage-backed deployment):")
        for k in missing_optional:
            print(f"- {k}")

    if not args.skip_migration_check:
        print("[2/3] Checking alembic migration state...")
        try:
            ok, heads, current = _check_migrations()
        except Exception as exc:
            print(f"Migration check failed to run: {exc}")
            return 1

        print(f"heads:   {heads}")
        print(f"current: {current}")
        if not ok:
            print("Migration state mismatch: current revision is not at head")
            return 1
        print("Migration state: OK")
    else:
        print("[2/3] Skipped migration check")

    if args.backend_url:
        print("[3/3] Checking backend health endpoint...")
        ok, detail = _check_health(args.backend_url)
        print(f"health detail: {detail}")
        if not ok:
            print("Health check failed")
            return 1
        print("Health check: OK")
    else:
        print("[3/3] Skipped remote health check (no --backend-url)")

    print("\nDeployment checks PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
