from __future__ import annotations

import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SAVE_SERVICE_BASE_URL = os.getenv("SAVE_SERVICE_BASE_URL", "http://127.0.0.1:8010").rstrip("/")
SAVE_SERVICE_TIMEOUT_SECONDS = float(os.getenv("SAVE_SERVICE_TIMEOUT_SECONDS", "2.5"))
SAVE_SERVICE_RETRIES = int(os.getenv("SAVE_SERVICE_RETRIES", "1"))
SAVE_SERVICE_API_TOKEN = os.getenv("SAVE_SERVICE_API_TOKEN", "")
NAMESPACE = "sncf-connect"


class SaveServiceError(RuntimeError):
    pass


def _request_json(path: str, method: str = "GET", payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if SAVE_SERVICE_API_TOKEN:
        headers["X-API-Token"] = SAVE_SERVICE_API_TOKEN
    request = Request(f"{SAVE_SERVICE_BASE_URL}{path}", data=data, method=method, headers=headers)

    attempts = max(1, SAVE_SERVICE_RETRIES + 1)
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with urlopen(request, timeout=SAVE_SERVICE_TIMEOUT_SECONDS) as response:
                raw = response.read().decode("utf-8") or "{}"
                return json.loads(raw)
        except HTTPError as err:
            if err.code == 404:
                return {}
            last_error = err
        except (URLError, TimeoutError, ValueError) as err:
            last_error = err
        if attempt < attempts:
            time.sleep(0.15 * attempt)
    raise SaveServiceError(f"Save service unavailable: {last_error}")


def save_session(session_id: str, payload: dict) -> None:
    _request_json(
        "/v1/state",
        method="POST",
        payload={
            "namespace": NAMESPACE,
            "key": session_id,
            "payload": payload,
            "version": 1,
        },
    )


def load_session(session_id: str) -> dict | None:
    data = _request_json(f"/v1/state/{NAMESPACE}/{session_id}", method="GET")
    if "payload" not in data:
        return None
    return data["payload"]


def delete_session(session_id: str) -> None:
    _request_json(f"/v1/state/{NAMESPACE}/{session_id}", method="DELETE")
