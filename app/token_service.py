import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

from .models import MockUser


TOKEN_SECRET = os.getenv("TOKEN_SECRET", os.getenv("SESSION_SECRET", "dev-secret-change-me"))
TOKEN_TTL_SECONDS = int(os.getenv("TOKEN_TTL_SECONDS", "900"))
TOKEN_ISSUER = os.getenv("TOKEN_ISSUER", "sncf-connect-monopoly")


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _b64decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(f"{raw}{padding}")


def _sign(data: str) -> str:
    digest = hmac.new(TOKEN_SECRET.encode("utf-8"), data.encode("utf-8"), hashlib.sha256).digest()
    return _b64encode(digest)


def build_access_token(user: MockUser) -> tuple[str, int]:
    issued_at = int(time.time())
    expires_at = issued_at + TOKEN_TTL_SECONDS
    claims: dict[str, Any] = {
        "sub": user.sub,
        "given_name": user.given_name,
        "family_name": user.family_name,
        "email": user.email,
        "iat": issued_at,
        "exp": expires_at,
        "iss": TOKEN_ISSUER,
    }
    body = json.dumps(claims, separators=(",", ":"), sort_keys=True)
    body_b64 = _b64encode(body.encode("utf-8"))
    signature = _sign(body_b64)
    return f"{body_b64}.{signature}", TOKEN_TTL_SECONDS


def introspect_access_token(token: str) -> dict[str, Any]:
    parts = token.split(".", 1)
    if len(parts) != 2:
        return {"active": False}
    body_b64, signature = parts
    expected = _sign(body_b64)
    if not hmac.compare_digest(signature, expected):
        return {"active": False}
    try:
        payload = json.loads(_b64decode(body_b64).decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return {"active": False}

    exp = int(payload.get("exp", 0))
    if exp <= int(time.time()):
        return {"active": False}

    return {
        "active": True,
        "sub": payload.get("sub"),
        "given_name": payload.get("given_name"),
        "family_name": payload.get("family_name"),
        "email": payload.get("email"),
        "exp": exp,
    }
