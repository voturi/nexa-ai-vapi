"""Booking service."""
import uuid
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
import structlog

import app.models  # noqa: F401 — ensures all FK targets are registered
from app.models.booking import Booking
from app.models.tenant import Tenant

logger = structlog.get_logger()


class BookingService:
    """Service for booking operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Booking]:
        """List bookings for a tenant."""
        query = (
            select(Booking)
            .where(Booking.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
            .order_by(Booking.scheduled_at.desc())
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_by_id(self, booking_id: UUID) -> Optional[Booking]:
        """Get booking by ID."""
        result = await self.db.execute(select(Booking).where(Booking.id == booking_id))
        return result.scalar_one_or_none()

    async def create(
        self,
        tenant_id: UUID,
        service_id: str,
        customer_name: str,
        customer_phone: str,
        scheduled_at: datetime,
        customer_email: Optional[str] = None,
        notes: Optional[str] = None,
        call_id: Optional[UUID] = None,
        service_name: Optional[str] = None,
        duration_minutes: int = 60,
        timezone: Optional[str] = None,
        booking_metadata: Optional[dict] = None,
    ) -> Booking:
        """Create a booking record."""
        booking = Booking(
            tenant_id=tenant_id,
            call_id=call_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_email=customer_email,
            service_id=service_id,
            service_name=service_name,
            scheduled_at=scheduled_at,
            duration_minutes=duration_minutes,
            timezone=timezone,
            status="confirmed",
            notes=notes,
            booking_metadata=booking_metadata,
        )
        self.db.add(booking)
        await self.db.commit()
        await self.db.refresh(booking)
        logger.info(
            "booking_created",
            booking_id=str(booking.id),
            tenant_id=str(tenant_id),
            customer_name=customer_name,
            scheduled_at=str(scheduled_at),
        )
        return booking

    async def create_from_tool_call(
        self,
        tenant: Tenant,
        parameters: dict,
        call_id: Optional[UUID] = None,
    ) -> Booking:
        """
        Create a booking from a VAPI tool call's parameters.

        Handles ISO datetime parsing and service lookup from tenant.services.
        """
        service_id = parameters.get("service_id", "")
        customer_name = parameters.get("customer_name", "Customer")
        customer_phone = parameters.get("customer_phone", "")
        customer_email = parameters.get("customer_email")
        address = parameters.get("address")
        notes = parameters.get("notes")
        scheduled_datetime_str = parameters.get("scheduled_datetime", "")

        # Parse scheduled datetime
        try:
            scheduled_at = datetime.fromisoformat(
                scheduled_datetime_str.replace("Z", "+00:00")
            ).replace(tzinfo=None)
            # Ensure year is correct
            if scheduled_at.year < 2026:
                scheduled_at = scheduled_at.replace(year=datetime.now().year)
        except Exception:
            scheduled_at = datetime.utcnow()

        # Resolve service name and duration from tenant config
        service_name = service_id
        duration_minutes = 60
        services = tenant.services or []
        for svc in services:
            if svc.get("id") == service_id:
                service_name = svc.get("name", service_id)
                duration_minutes = svc.get("duration_minutes", 60)
                break

        booking_metadata = {}
        if address:
            booking_metadata["address"] = address

        return await self.create(
            tenant_id=tenant.id,
            service_id=service_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_email=customer_email,
            notes=notes,
            scheduled_at=scheduled_at,
            call_id=call_id,
            service_name=service_name,
            duration_minutes=duration_minutes,
            timezone=tenant.timezone,
            booking_metadata=booking_metadata or None,
        )

    async def update(self, booking_id: UUID, booking_data: dict) -> Optional[Booking]:
        """Update booking fields."""
        booking = await self.get_by_id(booking_id)
        if not booking:
            return None
        for key, value in booking_data.items():
            if hasattr(booking, key):
                setattr(booking, key, value)
        booking.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(booking)
        return booking

    async def cancel(self, booking_id: UUID, reason: Optional[str] = None) -> Optional[Booking]:
        """Cancel a booking."""
        booking = await self.get_by_id(booking_id)
        if not booking:
            return None
        booking.status = "cancelled"
        booking.cancelled_at = datetime.utcnow()
        booking.cancellation_reason = reason
        await self.db.commit()
        await self.db.refresh(booking)
        logger.info("booking_cancelled", booking_id=str(booking_id))
        return booking
