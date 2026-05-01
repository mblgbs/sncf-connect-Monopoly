from __future__ import annotations

import io
import json
import urllib.error
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


class _MockResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> "_MockResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        return None


client = TestClient(app)


def test_ticket_payment_link_success() -> None:
    with patch(
        "app.main.urllib.request.urlopen",
        return_value=_MockResponse({"url": "https://buy.stripe.com/test_sncf_123"}),
    ) as mocked_urlopen:
        response = client.post(
            "/tickets/payment-link",
            json={"ticket_id": "ticket_123", "amount_hint_cents": 4200},
        )

    assert response.status_code == 200
    assert response.json() == {"url": "https://buy.stripe.com/test_sncf_123"}
    request = mocked_urlopen.call_args.args[0]
    body = json.loads(request.data.decode("utf-8"))
    assert body["amount_hint_cents"] == 4200


def test_ticket_payment_link_upstream_error() -> None:
    error = urllib.error.HTTPError(
        url="http://127.0.0.1:8004/payments/link",
        code=502,
        msg="Bad Gateway",
        hdrs=None,
        fp=io.BytesIO(b'{"detail":"Stripe indisponible"}'),
    )
    with patch("app.main.urllib.request.urlopen", side_effect=error):
        response = client.post("/tickets/payment-link", json={"ticket_id": "ticket_999"})

    assert response.status_code == 502
    assert response.json()["detail"] == "Stripe indisponible"
