"""Booking service."""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID


class BookingService:
    """Service for booking operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List:
        """List bookings for a tenant."""
        # TODO: Implement
        return []

    async def get_by_id(self, booking_id: UUID):
        """Get booking by ID."""
        # TODO: Implement
        return None

    async def create(self, tenant_id: UUID, booking_data):
        """Create a booking."""
        # TODO: Implement
        raise NotImplementedError("Booking creation not yet implemented")

    async def update(self, booking_id: UUID, booking_data):
        """Update booking."""
        # TODO: Implement
        raise NotImplementedError("Booking update not yet implemented")

    async def cancel(self, booking_id: UUID):
        """Cancel booking."""
        # TODO: Implement
        raise NotImplementedError("Booking cancellation not yet implemented")
