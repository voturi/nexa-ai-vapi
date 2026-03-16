"""Analytics API endpoints."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from app.core.database import get_db
from app.core.auth import get_current_user_tenant
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_tenant=Depends(get_current_user_tenant),
):
    """Get dashboard summary stats (today, this week, recent activity)."""
    service = AnalyticsService(db)
    return await service.get_dashboard_stats(tenant_id=current_tenant.id)


@router.get("/overview")
async def get_overview(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_tenant=Depends(get_current_user_tenant),
):
    """Get analytics overview for date range."""
    service = AnalyticsService(db)
    return await service.get_overview(
        tenant_id=current_tenant.id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/calls")
async def get_call_metrics(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_tenant=Depends(get_current_user_tenant),
):
    """Get call metrics for date range."""
    service = AnalyticsService(db)
    return await service.get_call_metrics(
        tenant_id=current_tenant.id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/bookings")
async def get_booking_metrics(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_tenant=Depends(get_current_user_tenant),
):
    """Get booking metrics for date range."""
    service = AnalyticsService(db)
    return await service.get_booking_metrics(
        tenant_id=current_tenant.id,
        start_date=start_date,
        end_date=end_date,
    )
