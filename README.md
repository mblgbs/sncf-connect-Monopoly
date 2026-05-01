# SNCF Connect Monopoly - Mock Authentication (FastAPI)

This project provides a minimal digital authentication device that simulates an SNCF Connect-like OAuth flow.

**Écosystème Monopoly :** [services-Monopoly-](../services-Monopoly-/README.md#decouverte-des-services-ecosystem) — `GET http://127.0.0.1:8004/ecosystem` (ce service : `8005` par défaut).

## Features

- Mock login flow with redirect/callback.
- `state` validation to prevent CSRF in OAuth redirection.
- Signed cookie-based local session (`HttpOnly`, configurable `Secure` and `SameSite`).
- Protected endpoint (`/me`) requiring authentication.
- Logout endpoint that clears the session.
- Access token issuance endpoint for API clients.
- Token introspection endpoint for downstream services.

## Requirements

- Python 3.10+

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and adjust values as needed.

Important variables:

- `APP_BASE_URL`: base URL used for redirects (default `http://127.0.0.1:8005`)
- `PORT`: local API port (recommended `8005`)
- `SESSION_SECRET`: signing secret for the cookie session
- `SESSION_COOKIE_NAME`: session cookie key
- `SESSION_SECURE`: set `true` in HTTPS environments
- `SESSION_SAMESITE`: cookie same-site policy (`lax`, `strict`, `none`)
- `TOKEN_SECRET`: signing secret for issued access tokens
- `TOKEN_TTL_SECONDS`: access token lifetime (default `900`)
- `TOKEN_ISSUER`: token issuer string used in metadata

## Run

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8005
```

## Manual test scenario

1. Open `http://127.0.0.1:8005/auth/login` in your browser.
2. Follow redirects through `/mock-sncf-connect/authorize` and `/auth/callback`.
3. Call `GET /me` to retrieve the authenticated mock user.
4. Call `POST /auth/logout`.
5. Call `GET /me` again: it should return `401 Authentication required`.

## SSO API flow (MVP)

1. Run this service (IdP) and authenticate once via browser on `/auth/login`.
2. Call `POST /auth/token` with the session cookie to retrieve an `access_token`.
3. Call protected APIs with `Authorization: Bearer <access_token>`.
4. Consumer services validate tokens against `GET /auth/introspect`.

### Example cURL flow

```bash
# 1) Authenticate and keep cookie
curl -i -c cookies.txt "http://127.0.0.1:8005/auth/login"

# 2) Follow browser redirects manually once (or open /auth/login in browser),
#    then request a token using the same cookie jar
curl -s -b cookies.txt -X POST "http://127.0.0.1:8005/auth/token"

# 3) Use token on consumer services (examples — point them at this base URL if integrated)
curl -H "Authorization: Bearer <token>" "http://127.0.0.1:8002/comptes"
```

### Integrate a new API service

Set these variables on the target service (pattern mirrors FranceConnect integration):

- `SERVICE_AUTH_ENABLED=true`
- Base URL of this mock (e.g. `http://127.0.0.1:8005`) as the introspection host
- `AUTH_REQUEST_TIMEOUT_SECONDS=2.5` (Python services) or `AUTH_REQUEST_TIMEOUT_MS=2500` (Node)

The target service must:

1. Read `Authorization: Bearer <token>`.
2. Call `GET /auth/introspect` on this SNCF Connect mock.
3. Allow request only when `active=true`.

## Endpoints

- `GET /` healthcheck
- `GET /auth/login` start authentication
- `GET /mock-sncf-connect/authorize` mocked provider authorize endpoint
- `GET /auth/callback` callback consuming `code` and `state`
- `GET /me` protected user profile
- `POST /auth/logout` clear session
- `POST /auth/token` issue `access_token` from authenticated session
- `GET /auth/introspect` validate bearer token
- `GET /auth/config` return MVP auth metadata
- `GET /jwks-or-config` simplified discovery helper

## Paiement ticket (Stripe)

- Nouveau endpoint: `POST /tickets/payment-link`.
- Payload: `{ "ticket_id": "...", "metadata": { ... } }`.
- Reponse: `{ "url": "https://buy.stripe.com/..." }`.
- Le service appelle le gateway `services-Monopoly-` via `SERVICES_MONOPOLY_BASE_URL`.
