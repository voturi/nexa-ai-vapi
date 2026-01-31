"""Tenant API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_tenant
from app.schemas.tenant import TenantCreate, TenantUpdate, TenantResponse
from app.services.tenant_service import TenantService

router = APIRouter()


@router.post("", response_model=TenantResponse)
async def create_tenant(
    tenant_data: TenantCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new tenant."""
    service = TenantService(db)
    return await service.create(tenant_data)


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_tenant = Depends(get_current_tenant),
):
    """Get tenant by ID."""
    service = TenantService(db)
    tenant = await service.get_by_id(tenant_id)

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Ensure user can only access their own tenant
    if str(tenant.id) != str(current_tenant.id):
        raise HTTPException(status_code=403, detail="Access denied")

    return tenant


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: UUID,
    tenant_data: TenantUpdate,
    db: AsyncSession = Depends(get_db),
    current_tenant = Depends(get_current_tenant),
):
    """Update tenant."""
    if str(tenant_id) != str(current_tenant.id):
        raise HTTPException(status_code=403, detail="Access denied")

    service = TenantService(db)
    return await service.update(tenant_id, tenant_data)


@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_tenant = Depends(get_current_tenant),
):
    """Delete tenant."""
    if str(tenant_id) != str(current_tenant.id):
        raise HTTPException(status_code=403, detail="Access denied")

    service = TenantService(db)
    await service.delete(tenant_id)
    return {"message": "Tenant deleted successfully"}
