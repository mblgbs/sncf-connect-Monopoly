import base64
import hashlib
import hmac
import json
import os
import secrets
from typing import Any

from fastapi import HTTPException, Request, Response, status

from .models import MockUser, SessionPayload
from .save_service_client import SaveServiceError, delete_session, load_session, save_session


SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "sncf_monopoly_session")
SESSION_SECRET = os.getenv("SESSION_SECRET", "dev-secret-change-me")
SESSION_SAMESITE = os.getenv("SESSION_SAMESITE", "lax").lower()
SESSION_SECURE = os.getenv("SESSION_SECURE", "false").lower() == "true"


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _b64decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(f"{raw}{padding}")


def _sign(data: str) -> str:
    digest = hmac.new(SESSION_SECRET.encode("utf-8"), data.encode("utf-8"), hashlib.sha256).digest()
    return _b64encode(digest)


def _serialize(payload: SessionPayload) -> str:
    body = json.dumps(payload.model_dump(), separators=(",", ":"), sort_keys=True)
    body_b64 = _b64encode(body.encode("utf-8"))
    signature = _sign(body_b64)
    return f"{body_b64}.{signature}"


def _deserialize(raw_cookie: str) -> SessionPayload:
    try:
        body_b64, signature = raw_cookie.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session format") from exc

    expected = _sign(body_b64)
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session signature")

    try:
        body = _b64decode(body_b64).decode("utf-8")
        parsed: dict[str, Any] = json.loads(body)
        return SessionPayload.model_validate(parsed)
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session payload") from exc


def set_session(response: Response, payload: SessionPayload) -> None:
    session_id = payload.session_id or secrets.token_urlsafe(20)
    payload_with_id = SessionPayload(session_id=session_id, state=payload.state, user=payload.user)
    try:
        save_session(session_id, payload_with_id.model_dump())
    except SaveServiceError:
        # Keep cookie-only fallback if remote persistence is unavailable.
        pass
    token = _serialize(payload_with_id)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=SESSION_SECURE,
        samesite=SESSION_SAMESITE,  # type: ignore[arg-type]
        max_age=3600,
        path="/",
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")


def get_session(request: Request) -> SessionPayload:
    raw_cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if not raw_cookie:
        return SessionPayload()
    payload = _deserialize(raw_cookie)
    if payload.session_id:
        try:
            stored = load_session(payload.session_id)
            if stored is not None:
                return SessionPayload.model_validate(stored)
        except SaveServiceError:
            # Keep old behavior by falling back to cookie data.
            return payload
    return payload


def revoke_session(request: Request, response: Response) -> None:
    payload = get_session(request)
    if payload.session_id:
        try:
            delete_session(payload.session_id)
        except SaveServiceError:
            pass
    clear_session(response)


def get_current_user(request: Request) -> MockUser:
    payload = get_session(request)
    if payload.user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return payload.user
