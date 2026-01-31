"""Call service."""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID


class CallService:
    """Service for call operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List:
        """List calls for a tenant."""
        # TODO: Implement
        return []

    async def get_by_id(self, call_id: UUID):
        """Get call by ID."""
        # TODO: Implement
        return None

    async def handle_call_ended(self, data: dict):
        """Handle call ended webhook."""
        # TODO: Implement
        pass

    async def handle_call_status(self, data: dict):
        """Handle call status webhook."""
        # TODO: Implement
        pass
