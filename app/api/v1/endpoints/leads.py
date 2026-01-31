"""Lead API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_tenant
from app.schemas.lead import LeadResponse, LeadUpdate
from app.services.lead_service import LeadService

router = APIRouter()


@router.get("", response_model=List[LeadResponse])
async def list_leads(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_tenant = Depends(get_current_tenant),
):
    """List leads for current tenant."""
    service = LeadService(db)
    return await service.list_by_tenant(
        tenant_id=current_tenant.id,
        skip=skip,
        limit=limit
    )


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_tenant = Depends(get_current_tenant),
):
    """Get lead by ID."""
    service = LeadService(db)
    lead = await service.get_by_id(lead_id)

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if str(lead.tenant_id) != str(current_tenant.id):
        raise HTTPException(status_code=403, detail="Access denied")

    return lead


@router.put("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: UUID,
    lead_data: LeadUpdate,
    db: AsyncSession = Depends(get_db),
    current_tenant = Depends(get_current_tenant),
):
    """Update lead status."""
    service = LeadService(db)
    lead = await service.get_by_id(lead_id)

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if str(lead.tenant_id) != str(current_tenant.id):
        raise HTTPException(status_code=403, detail="Access denied")

    return await service.update(lead_id, lead_data)
