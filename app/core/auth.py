"""Supabase JWT authentication middleware.

Validates Supabase-issued JWTs and resolves the authenticated user to a tenant.
Works alongside the existing API key auth — endpoints can use either dependency.

Flow:
  1. Frontend logs in via Supabase Auth (email/password, magic link, etc.)
  2. Frontend sends Supabase JWT as Bearer token to backend
  3. This middleware decodes the JWT using the Supabase JWT secret
  4. Extracts the user ID (sub claim)
  5. Looks up the tenant linked to that user (via tenants.supabase_user_id column)
  6. Returns the Tenant object to the endpoint
"""
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.tenant import Tenant

logger = structlog.get_logger()

_bearer = HTTPBearer()

# Supabase uses HS256 JWTs signed with the JWT secret
_ALGORITHM = "HS256"


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
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=[_ALGORITHM],
            audience="authenticated",
        )
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
