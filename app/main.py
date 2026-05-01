import json
import os
import urllib.error
import urllib.request

from fastapi import Depends, FastAPI, HTTPException, status

from .auth import mock_router, router as auth_router
from .models import MessageResponse, MockUser, PaymentLinkResponse, TicketPaymentLinkRequest
from .session import get_current_user


app = FastAPI(title=os.getenv("APP_NAME", "SNCF Connect Monopoly Mock"))
app.include_router(auth_router)
app.include_router(mock_router)


@app.get("/", response_model=MessageResponse)
def healthcheck() -> MessageResponse:
    return MessageResponse(message="Service is running")


@app.get("/me", response_model=MockUser)
def me(current_user: MockUser = Depends(get_current_user)) -> MockUser:
    return current_user


@app.get("/jwks-or-config")
def jwks_or_config() -> dict[str, str]:
    return {
        "note": "MVP config endpoint; use /auth/config for service integration details.",
        "config_url": f"{os.getenv('APP_BASE_URL', 'http://127.0.0.1:8005')}/auth/config",
    }


def _services_monopoly_base_url() -> str:
    return os.getenv("SERVICES_MONOPOLY_BASE_URL", "http://127.0.0.1:8004").strip().rstrip("/")


def _request_payment_link(payload: TicketPaymentLinkRequest) -> str:
    services_payload = {
        "app": "sncf_connect",
        "context": "ticket",
        "reference_id": payload.ticket_id,
        "metadata": payload.metadata or {},
    }
    if payload.amount_hint_cents is not None:
        services_payload["amount_hint_cents"] = payload.amount_hint_cents

    body = json.dumps(services_payload).encode("utf-8")
    request = urllib.request.Request(
        url=f"{_services_monopoly_base_url()}/payments/link",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=5.0) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = "Erreur service paiements"
        try:
            upstream = json.loads(exc.read().decode("utf-8"))
            if isinstance(upstream, dict):
                raw_detail = upstream.get("detail") or upstream.get("error")
                if isinstance(raw_detail, str) and raw_detail.strip():
                    detail = raw_detail.strip()
        except (UnicodeDecodeError, ValueError):
            pass
        raise RuntimeError(detail) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("Service paiements indisponible") from exc

    payment_url = data.get("url") if isinstance(data, dict) else None
    if not isinstance(payment_url, str) or not payment_url.strip():
        raise RuntimeError("Reponse paiement invalide")

    return payment_url


@app.post("/tickets/payment-link", response_model=PaymentLinkResponse)
def create_ticket_payment_link(payload: TicketPaymentLinkRequest) -> PaymentLinkResponse:
    try:
        payment_url = _request_payment_link(payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return PaymentLinkResponse(url=payment_url)
