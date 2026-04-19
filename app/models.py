from pydantic import BaseModel, Field


class MockUser(BaseModel):
    sub: str = Field(..., description="SNCF Connect unique subject identifier")
    given_name: str
    family_name: str
    email: str


class SessionPayload(BaseModel):
    session_id: str | None = None
    state: str | None = None
    user: MockUser | None = None


class MessageResponse(BaseModel):
    message: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class IntrospectionResponse(BaseModel):
    active: bool
    sub: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    email: str | None = None
    exp: int | None = None
