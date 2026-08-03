import time
from datetime import datetime, timezone

import httpx
from jose import jwt, JWTError
from fastapi import HTTPException, status

from config import get_settings

settings = get_settings()

_JWKS_CACHE: dict = {"keys": [], "fetched_at": 0.0}
_JWKS_TTL_SECONDS = 3600


def _get_jwks() -> list[dict]:
    """Fetches (and caches) Supabase's public JWKS, used to verify tokens
    signed with the newer asymmetric key system (ES256/RS256). Supabase
    projects created before that migration still sign with a shared HS256
    secret instead — see decode_supabase_jwt for the fallback.
    """
    now = time.time()
    if _JWKS_CACHE["keys"] and (now - _JWKS_CACHE["fetched_at"]) < _JWKS_TTL_SECONDS:
        return _JWKS_CACHE["keys"]

    url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
    try:
        resp = httpx.get(url, timeout=5.0)
        resp.raise_for_status()
        keys = resp.json().get("keys", [])
    except Exception:  # noqa: BLE001 — fall back to whatever was cached, if anything
        return _JWKS_CACHE["keys"]

    _JWKS_CACHE["keys"] = keys
    _JWKS_CACHE["fetched_at"] = now
    return keys


def decode_supabase_jwt(token: str) -> dict:
    """Decode & verify a Supabase-issued access token.

    Newer Supabase projects sign access tokens asymmetrically (ES256/RS256)
    and publish the public keys via a JWKS endpoint; older projects still
    sign with a shared HS256 secret (`SUPABASE_JWT_SECRET`). We inspect the
    token header to pick the right verification path.
    """
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Malformed token: {exc}") from exc

    alg = header.get("alg", settings.JWT_ALGORITHM)

    try:
        if alg == "HS256":
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
        else:
            kid = header.get("kid")
            matching_key = next((k for k in _get_jwks() if k.get("kid") == kid), None)
            if matching_key is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="No matching JWKS key found for token",
                )
            payload = jwt.decode(
                token,
                matching_key,
                algorithms=[alg],
                audience="authenticated",
            )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
        ) from exc

    exp = payload.get("exp")
    if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")

    return payload
