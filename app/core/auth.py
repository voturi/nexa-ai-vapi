"""Supabase JWT authentication middleware.

Validates Supabase-issued JWTs and resolves the authenticated user to a tenant.
Works alongside the existing API key auth — endpoints can use either dependency.

Supports both:
  - HS256 (older Supabase projects, uses SUPABASE_JWT_SECRET)
  - ES256 (newer Supabase projects, uses JWKS from Supabase)

Flow:
  1. Frontend logs in via Supabase Auth (email/password, magic link, etc.)
  2. Frontend sends Supabase JWT as Bearer token to backend
  3. This middleware decodes the JWT using the appropriate key
  4. Extracts the user ID (sub claim)
  5. Looks up the tenant linked to that user (via tenants.supabase_user_id column)
  6. Returns the Tenant object to the endpoint
"""
import json
from typing import Optional

import httpx
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt, jwk
from jose.utils import base64url_decode
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.tenant import Tenant

logger = structlog.get_logger()

_bearer = HTTPBearer()

# Cached JWKS keys (loaded once on first request)
_jwks_cache: Optional[dict] = None


def _get_jwks() -> dict:
    """Fetch and cache JWKS from Supabase."""
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache

    jwks_url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
    try:
        resp = httpx.get(jwks_url, timeout=10)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        logger.info("jwks_loaded", keys_count=len(_jwks_cache.get("keys", [])))
        return _jwks_cache
    except Exception as e:
        logger.error("jwks_fetch_failed", error=str(e))
        return {"keys": []}


def _decode_jwt(token: str) -> dict:
    """
    Decode a Supabase JWT, auto-detecting HS256 vs ES256.

    For HS256: uses SUPABASE_JWT_SECRET directly.
    For ES256: fetches the public key from Supabase JWKS endpoint.
    """
    # Peek at the header to determine algorithm
    header_segment = token.split(".")[0]
    # Add padding
    header_segment += "=" * (4 - len(header_segment) % 4)
    header = json.loads(base64url_decode(header_segment.encode()))
    alg = header.get("alg", "HS256")

    if alg == "HS256":
        return jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )

    if alg == "ES256":
        kid = header.get("kid")
        jwks_data = _get_jwks()

        # Find the matching key
        key_data = None
        for key in jwks_data.get("keys", []):
            if key.get("kid") == kid:
                key_data = key
                break

        if not key_data:
            raise JWTError(f"No matching JWKS key found for kid={kid}")

        public_key = jwk.construct(key_data, algorithm="ES256")
        return jwt.decode(
            token,
            public_key,
            algorithms=["ES256"],
            audience="authenticated",
        )

    raise JWTError(f"Unsupported JWT algorithm: {alg}")


async def get_current_user_tenant(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """
    Validate a Supabase JWT and return the linked Tenant.

    Usage in endpoints:
        @router.get("/something")
        async def my_endpoint(tenant = Depends(get_current_user_tenant)):
            ...
    """
    token = credentials.credentials

    # Decode and validate the JWT
    try:
        payload = _decode_jwt(token)
    except JWTError as e:
        logger.warning("jwt_validation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract user ID from the 'sub' claim
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user identifier",
        )

    # Resolve user → tenant
    result = await db.execute(
        select(Tenant).where(
            Tenant.supabase_user_id == user_id,
            Tenant.is_active == True,
            Tenant.deleted_at.is_(None),
        )
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        logger.warning("jwt_user_no_tenant", user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No business account linked to this user",
        )

    return tenant
