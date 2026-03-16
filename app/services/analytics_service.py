"""Analytics service."""
from datetime import date, datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select, and_, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.call import Call
from app.models.lead import Lead


class AnalyticsService:
    """Service for analytics operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_overview(
        self,
        tenant_id: UUID,
        start_date: date,
        end_date: date,
    ) -> dict:
        """Get analytics overview — total calls, bookings, leads in date range."""
        # Convert dates to datetime range
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        total_calls = await self._count(Call, tenant_id, Call.created_at, start_dt, end_dt)
        total_bookings = await self._count(Booking, tenant_id, Booking.created_at, start_dt, end_dt)
        total_leads = await self._count(Lead, tenant_id, Lead.created_at, start_dt, end_dt)

        # Booking conversion rate
        conversion_rate = (total_bookings / total_calls * 100) if total_calls > 0 else 0

        # Average call duration
        avg_duration_result = await self.db.execute(
            select(func.avg(Call.duration_seconds)).where(
                Call.tenant_id == tenant_id,
                Call.created_at >= start_dt,
                Call.created_at <= end_dt,
                Call.duration_seconds.isnot(None),
            )
        )
        avg_duration = avg_duration_result.scalar() or 0

        return {
            "total_calls": total_calls,
            "total_bookings": total_bookings,
            "total_leads": total_leads,
            "conversion_rate": round(conversion_rate, 1),
            "avg_call_duration_seconds": round(float(avg_duration)),
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        }

    async def get_call_metrics(
        self,
        tenant_id: UUID,
        start_date: date,
        end_date: date,
    ) -> dict:
        """Get call metrics — daily counts and outcome breakdown."""
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        # Daily call counts
        daily_result = await self.db.execute(
            select(
                cast(Call.created_at, Date).label("day"),
                func.count(Call.id).label("count"),
            )
            .where(
                Call.tenant_id == tenant_id,
                Call.created_at >= start_dt,
                Call.created_at <= end_dt,
            )
            .group_by(cast(Call.created_at, Date))
            .order_by(cast(Call.created_at, Date))
        )
        daily_calls = [
            {"date": str(row.day), "count": row.count}
            for row in daily_result.all()
        ]

        # Outcome breakdown
        outcome_result = await self.db.execute(
            select(
                Call.outcome,
                func.count(Call.id).label("count"),
            )
            .where(
                Call.tenant_id == tenant_id,
                Call.created_at >= start_dt,
                Call.created_at <= end_dt,
            )
            .group_by(Call.outcome)
        )
        outcomes = {
            (row.outcome or "unknown"): row.count
            for row in outcome_result.all()
        }

        return {
            "daily": daily_calls,
            "outcomes": outcomes,
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        }

    async def get_booking_metrics(
        self,
        tenant_id: UUID,
        start_date: date,
        end_date: date,
    ) -> dict:
        """Get booking metrics — daily counts and status breakdown."""
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        # Daily booking counts
        daily_result = await self.db.execute(
            select(
                cast(Booking.created_at, Date).label("day"),
                func.count(Booking.id).label("count"),
            )
            .where(
                Booking.tenant_id == tenant_id,
                Booking.created_at >= start_dt,
                Booking.created_at <= end_dt,
            )
            .group_by(cast(Booking.created_at, Date))
            .order_by(cast(Booking.created_at, Date))
        )
        daily_bookings = [
            {"date": str(row.day), "count": row.count}
            for row in daily_result.all()
        ]

        # Status breakdown
        status_result = await self.db.execute(
            select(
                Booking.status,
                func.count(Booking.id).label("count"),
            )
            .where(
                Booking.tenant_id == tenant_id,
                Booking.created_at >= start_dt,
                Booking.created_at <= end_dt,
            )
            .group_by(Booking.status)
        )
        statuses = {
            row.status: row.count
            for row in status_result.all()
        }

        return {
            "daily": daily_bookings,
            "statuses": statuses,
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        }

    async def get_dashboard_stats(self, tenant_id: UUID) -> dict:
        """
        Get dashboard summary stats — designed for the frontend dashboard.

        Returns today's stats, this week's stats, and recent activity.
        """
        now = datetime.utcnow()
        today_start = datetime.combine(now.date(), datetime.min.time())
        week_start = today_start - timedelta(days=now.weekday())  # Monday

        # Today's numbers
        today_calls = await self._count(Call, tenant_id, Call.created_at, today_start, now)
        today_bookings = await self._count(Booking, tenant_id, Booking.created_at, today_start, now)
        today_leads = await self._count(Lead, tenant_id, Lead.created_at, today_start, now)

        # This week's numbers
        week_calls = await self._count(Call, tenant_id, Call.created_at, week_start, now)
        week_bookings = await self._count(Booking, tenant_id, Booking.created_at, week_start, now)
        week_leads = await self._count(Lead, tenant_id, Lead.created_at, week_start, now)

        # Recent calls (last 5)
        recent_calls_result = await self.db.execute(
            select(Call)
            .where(Call.tenant_id == tenant_id)
            .order_by(Call.created_at.desc())
            .limit(5)
        )
        recent_calls = [
            {
                "id": str(c.id),
                "caller_phone": c.caller_phone,
                "caller_name": c.caller_name,
                "status": c.status,
                "outcome": c.outcome,
                "duration_seconds": c.duration_seconds,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in recent_calls_result.scalars().all()
        ]

        # Upcoming bookings (next 5)
        upcoming_result = await self.db.execute(
            select(Booking)
            .where(
                Booking.tenant_id == tenant_id,
                Booking.scheduled_at >= now,
                Booking.status == "confirmed",
            )
            .order_by(Booking.scheduled_at.asc())
            .limit(5)
        )
        upcoming_bookings = [
            {
                "id": str(b.id),
                "customer_name": b.customer_name,
                "customer_phone": b.customer_phone,
                "service_name": b.service_name,
                "scheduled_at": b.scheduled_at.isoformat() if b.scheduled_at else None,
                "duration_minutes": b.duration_minutes,
            }
            for b in upcoming_result.scalars().all()
        ]

        week_conversion = (week_bookings / week_calls * 100) if week_calls > 0 else 0

        return {
            "today": {
                "calls": today_calls,
                "bookings": today_bookings,
                "leads": today_leads,
            },
            "this_week": {
                "calls": week_calls,
                "bookings": week_bookings,
                "leads": week_leads,
                "conversion_rate": round(week_conversion, 1),
            },
            "recent_calls": recent_calls,
            "upcoming_bookings": upcoming_bookings,
        }

    async def _count(self, model, tenant_id: UUID, date_col, start_dt, end_dt) -> int:
        """Helper to count rows in a date range for a tenant."""
        result = await self.db.execute(
            select(func.count(model.id)).where(
                model.tenant_id == tenant_id,
                date_col >= start_dt,
                date_col <= end_dt,
            )
        )
        return result.scalar() or 0
