"""Lead service."""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID


class LeadService:
    """Service for lead operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List:
        """List leads for a tenant."""
        # TODO: Implement
        return []

    async def get_by_id(self, lead_id: UUID):
        """Get lead by ID."""
        # TODO: Implement
        return None

    async def update(self, lead_id: UUID, lead_data):
        """Update lead."""
        # TODO: Implement
        raise NotImplementedError("Lead update not yet implemented")
