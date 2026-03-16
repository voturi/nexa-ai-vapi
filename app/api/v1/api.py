"""API v1 router."""
from fastapi import APIRouter

from app.api.v1.endpoints import tenants, calls, bookings, leads, analytics, integrations

api_router = APIRouter()

api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(calls.router, prefix="/calls", tags=["calls"])
api_router.include_router(bookings.router, prefix="/bookings", tags=["bookings"])
api_router.include_router(leads.router, prefix="/leads", tags=["leads"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
