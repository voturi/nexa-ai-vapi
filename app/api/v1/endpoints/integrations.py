"""Integration endpoints — OAuth flows and management."""
import hashlib
import secrets
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_tenant
from app.services.integration_service import IntegrationService

logger = structlog.get_logger()

router = APIRouter()

# In-memory store for OAuth state tokens (maps state -> tenant_id)
# In production, use Redis with short TTL
_oauth_states: dict[str, str] = {}

GOOGLE_CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]


def _build_google_flow() -> Flow:
    """Build Google OAuth flow from config."""
    if not settings.GOOGLE_OAUTH_CLIENT_ID or not settings.GOOGLE_OAUTH_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth not configured on this server",
        )

    client_config = {
        "web": {
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_OAUTH_REDIRECT_URI],
        }
    }

    flow = Flow.from_client_config(
        client_config,
        scopes=GOOGLE_CALENDAR_SCOPES,
        redirect_uri=settings.GOOGLE_OAUTH_REDIRECT_URI,
    )
    return flow


# --------------------------------------------------------------------------- #
# OAuth: Authorize (tenant must be authenticated)
# --------------------------------------------------------------------------- #

@router.get("/google-calendar/authorize")
async def google_calendar_authorize(
    tenant=Depends(get_current_tenant),
):
    """
    Start Google Calendar OAuth flow.

    Returns the authorization URL the frontend should redirect the user to.
    """
    flow = _build_google_flow()

    # Generate a CSRF-safe state token that encodes the tenant_id
    nonce = secrets.token_urlsafe(32)
    state = hashlib.sha256(f"{tenant.id}:{nonce}".encode()).hexdigest()
    _oauth_states[state] = str(tenant.id)

    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        state=state,
        prompt="consent",  # Force consent to always get refresh_token
    )

    logger.info(
        "google_calendar_oauth_started",
        tenant_id=str(tenant.id),
    )

    return {"authorization_url": authorization_url}


# --------------------------------------------------------------------------- #
# OAuth: Callback (no auth — Google redirects here)
# --------------------------------------------------------------------------- #

@router.get("/google-calendar/callback")
async def google_calendar_callback(
    code: str = Query(...),
    state: str = Query(...),
    error: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Google OAuth callback.

    Google redirects here after the user grants (or denies) access.
    Exchanges the auth code for tokens and stores them encrypted.
    """
    if error:
        logger.warning("google_calendar_oauth_denied", error=error)
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/integrations/google-calendar?error={error}"
        )

    # Validate state
    tenant_id = _oauth_states.pop(state, None)
    if not tenant_id:
        logger.warning("google_calendar_oauth_invalid_state", state=state)
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    # Exchange auth code for tokens
    flow = _build_google_flow()
    try:
        flow.fetch_token(code=code)
    except Exception as e:
        logger.error("google_calendar_token_exchange_failed", error=str(e))
        raise HTTPException(status_code=400, detail="Failed to exchange authorization code")

    creds = flow.credentials

    credentials_data = {
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "scopes": list(creds.scopes) if creds.scopes else GOOGLE_CALENDAR_SCOPES,
    }
    if creds.expiry:
        credentials_data["token_expiry"] = creds.expiry.isoformat()

    # Store encrypted credentials
    integration_service = IntegrationService(db)
    await integration_service.store_credentials(
        tenant_id=tenant_id,
        integration_type="google_calendar",
        credentials_data=credentials_data,
        config={"calendar_id": "primary"},  # Default to primary calendar
        integration_name="Google Calendar",
    )

    logger.info(
        "google_calendar_oauth_completed",
        tenant_id=tenant_id,
        has_refresh_token=bool(creds.refresh_token),
    )

    # Redirect to frontend success page
    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/integrations/google-calendar?success=true"
    )


# --------------------------------------------------------------------------- #
# Status & Management (tenant must be authenticated)
# --------------------------------------------------------------------------- #

@router.get("/google-calendar/status")
async def google_calendar_status(
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Check Google Calendar connection status for the current tenant."""
    integration_service = IntegrationService(db)
    integration = await integration_service.get_integration(
        tenant_id=tenant.id,
        integration_type="google_calendar",
    )

    if not integration:
        return {
            "connected": False,
            "integration_type": "google_calendar",
        }

    return {
        "connected": integration.status == "active",
        "integration_type": "google_calendar",
        "status": integration.status,
        "config": integration.config,
        "last_sync_at": integration.last_sync_at.isoformat() if integration.last_sync_at else None,
        "last_error": integration.last_error,
        "connected_at": integration.created_at.isoformat() if integration.created_at else None,
    }


@router.delete("/google-calendar/disconnect")
async def google_calendar_disconnect(
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Disconnect Google Calendar integration for the current tenant."""
    integration_service = IntegrationService(db)
    disconnected = await integration_service.disconnect(
        tenant_id=tenant.id,
        integration_type="google_calendar",
    )

    if not disconnected:
        raise HTTPException(status_code=404, detail="Integration not found")

    logger.info(
        "google_calendar_disconnected",
        tenant_id=str(tenant.id),
    )

    return {"status": "disconnected", "integration_type": "google_calendar"}


@router.get("/google-calendar/calendars")
async def google_calendar_list_calendars(
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """List available Google Calendars for the connected account."""
    from app.integrations.google_calendar_client import GoogleCalendarClient

    integration_service = IntegrationService(db)
    creds = await integration_service.get_credentials(
        tenant_id=tenant.id,
        integration_type="google_calendar",
    )

    if not creds:
        raise HTTPException(status_code=404, detail="Google Calendar not connected")

    client = GoogleCalendarClient(creds)
    try:
        calendars = await client.list_calendars()
    except Exception as e:
        logger.error("google_calendar_list_error", error=str(e))
        raise HTTPException(status_code=502, detail="Failed to fetch calendars from Google")

    # If token was refreshed, persist the new token
    if client.token_refreshed:
        await integration_service.update_credentials(
            tenant_id=tenant.id,
            integration_type="google_calendar",
            credentials_data=client.get_refreshed_credentials(),
        )

    return {"calendars": calendars}


@router.put("/google-calendar/config")
async def google_calendar_update_config(
    config: dict,
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Update Google Calendar config (e.g. which calendar_id to use)."""
    integration_service = IntegrationService(db)
    integration = await integration_service.update_config(
        tenant_id=tenant.id,
        integration_type="google_calendar",
        config=config,
    )

    if not integration:
        raise HTTPException(status_code=404, detail="Google Calendar not connected")

    return {"status": "updated", "config": integration.config}
