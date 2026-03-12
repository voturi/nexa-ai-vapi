"""Lead service."""
import uuid
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
import structlog

import app.models  # noqa: F401 — ensures all FK targets are registered
from app.models.lead import Lead
from app.models.tenant import Tenant

logger = structlog.get_logger()


class LeadService:
    """Service for lead operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Lead]:
        """List leads for a tenant."""
        query = (
            select(Lead)
            .where(Lead.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
            .order_by(Lead.created_at.desc())
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_by_id(self, lead_id: UUID) -> Optional[Lead]:
        """Get lead by ID."""
        result = await self.db.execute(select(Lead).where(Lead.id == lead_id))
        return result.scalar_one_or_none()

    async def create(
        self,
        tenant_id: UUID,
        customer_phone: str,
        customer_name: Optional[str] = None,
        customer_email: Optional[str] = None,
        notes: Optional[str] = None,
        interest: Optional[str] = None,
        call_id: Optional[UUID] = None,
    ) -> Lead:
        """Create a lead record."""
        lead = Lead(
            tenant_id=tenant_id,
            call_id=call_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_email=customer_email,
            notes=notes,
            lead_metadata={"interest": interest} if interest else None,
            lead_source="phone_call",
            status="new",
        )
        self.db.add(lead)
        await self.db.commit()
        await self.db.refresh(lead)
        logger.info(
            "lead_created",
            lead_id=str(lead.id),
            tenant_id=str(tenant_id),
            customer_name=customer_name,
        )
        return lead

    async def create_from_tool_call(
        self,
        tenant: Tenant,
        parameters: dict,
        call_id: Optional[UUID] = None,
    ) -> Lead:
        """Create a lead from a VAPI tool call's parameters."""
        return await self.create(
            tenant_id=tenant.id,
            customer_phone=parameters.get("customer_phone", ""),
            customer_name=parameters.get("customer_name"),
            customer_email=parameters.get("customer_email"),
            notes=parameters.get("notes"),
            interest=parameters.get("interest"),
            call_id=call_id,
        )

    async def update(self, lead_id: UUID, lead_data: dict) -> Optional[Lead]:
        """Update lead fields."""
        lead = await self.get_by_id(lead_id)
        if not lead:
            return None
        for key, value in lead_data.items():
            if hasattr(lead, key):
                setattr(lead, key, value)
        lead.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(lead)
        return lead
