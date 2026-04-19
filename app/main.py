import os

from fastapi import Depends, FastAPI

from .auth import mock_router, router as auth_router
from .models import MessageResponse, MockUser
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
