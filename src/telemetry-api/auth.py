"""Cognito JWT verification (signature, expiry, issuer, audience) with JWKS caching.

Set COGNITO_USER_POOL_ID and COGNITO_CLIENT_ID in the environment. For local
development only, AUTH_DEV_BYPASS=true re-enables the legacy "demo" token; it
is off by default and must never be enabled in a deployed environment.
"""

import os
import time
import threading
from typing import Optional

import httpx
from fastapi import Header, HTTPException
from jose import jwk, jwt
from jose.exceptions import JWTError
from jose.utils import base64url_decode

COGNITO_REGION = os.getenv("AWS_REGION", "us-east-1")
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID", "")
COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID", "")
AUTH_DEV_BYPASS = os.getenv("AUTH_DEV_BYPASS", "false").lower() == "true"

_JWKS_TTL_SECONDS = 3600
_jwks_cache: dict = {"keys": None, "fetched_at": 0.0}
_jwks_lock = threading.Lock()


def issuer() -> str:
    return f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}"


def _load_jwks(force: bool = False) -> list:
    with _jwks_lock:
        fresh = _jwks_cache["keys"] is not None and (time.time() - _jwks_cache["fetched_at"]) < _JWKS_TTL_SECONDS
        if fresh and not force:
            return _jwks_cache["keys"]
        resp = httpx.get(f"{issuer()}/.well-known/jwks.json", timeout=5.0)
        resp.raise_for_status()
        _jwks_cache["keys"] = resp.json()["keys"]
        _jwks_cache["fetched_at"] = time.time()
        return _jwks_cache["keys"]


def _find_key(kid: str) -> Optional[dict]:
    for force in (False, True):  # a second pass handles key rotation
        for key in _load_jwks(force=force):
            if key.get("kid") == kid:
                return key
    return None


def decode_and_verify(token: str) -> dict:
    """Verify a Cognito id/access token and return its claims or raise HTTPException(401)."""
    if not COGNITO_USER_POOL_ID or not COGNITO_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Auth is not configured (COGNITO_USER_POOL_ID / COGNITO_CLIENT_ID).")
    try:
        header = jwt.get_unverified_header(token)
        key = _find_key(header.get("kid", ""))
        if key is None:
            raise HTTPException(status_code=401, detail="Unknown signing key.")

        public_key = jwk.construct(key)
        message, encoded_sig = token.rsplit(".", 1)
        if not public_key.verify(message.encode("utf-8"), base64url_decode(encoded_sig.encode("utf-8"))):
            raise HTTPException(status_code=401, detail="Invalid token signature.")

        claims = jwt.get_unverified_claims(token)
        if claims.get("exp", 0) < time.time():
            raise HTTPException(status_code=401, detail="Token has expired.")
        if claims.get("iss") != issuer():
            raise HTTPException(status_code=401, detail="Invalid token issuer.")

        token_use = claims.get("token_use")
        if token_use == "id":
            if claims.get("aud") != COGNITO_CLIENT_ID:
                raise HTTPException(status_code=401, detail="Invalid token audience.")
        elif token_use == "access":
            if claims.get("client_id") != COGNITO_CLIENT_ID:
                raise HTTPException(status_code=401, detail="Invalid token client.")
        else:
            raise HTTPException(status_code=401, detail="Unsupported token type.")
        return claims
    except HTTPException:
        raise
    except (JWTError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail=f"Unable to fetch signing keys: {exc}")


async def verify_cognito_token(authorization: str = Header(None)) -> dict:
    """FastAPI dependency: requires a valid Cognito bearer token."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    token = authorization.split(" ", 1)[1].strip()

    if AUTH_DEV_BYPASS and token in ("demo", "mock-token"):
        return {"email": "dev@fleetpulse.local", "cognito:groups": ["FleetAdmins"], "dev_bypass": True}

    claims = decode_and_verify(token)
    claims.setdefault("email", claims.get("username", "unknown"))
    return claims


def user_groups(claims: dict) -> list:
    return list(claims.get("cognito:groups", []) or [])


def require_group(*allowed: str):
    """Dependency factory restricting an endpoint to the given Cognito groups."""
    from fastapi import Depends

    async def checker(claims: dict = Depends(verify_cognito_token)) -> dict:
        if claims.get("dev_bypass"):
            return claims
        if not set(user_groups(claims)) & set(allowed):
            raise HTTPException(status_code=403, detail=f"Requires one of the groups: {', '.join(allowed)}")
        return claims

    return checker
