"""Tenant API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_tenant
from app.schemas.tenant import TenantCreate, TenantUpdate, TenantResponse
from app.services.tenant_service import TenantService

router = APIRouter()


@router.get("", response_model=List[TenantResponse])
async def list_tenants(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """List all tenants (admin endpoint)."""
    service = TenantService(db)
    return await service.list_all(skip=skip, limit=limit)


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


@router.post("/{tenant_id}/regenerate-api-key")
async def regenerate_api_key(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_tenant = Depends(get_current_tenant),
):
    """Regenerate API key for a tenant."""
    if str(tenant_id) != str(current_tenant.id):
        raise HTTPException(status_code=403, detail="Access denied")

    service = TenantService(db)
    new_api_key = await service.regenerate_api_key(tenant_id)
    return {"api_key": new_api_key, "message": "API key regenerated successfully"}


@router.post("/{tenant_id}/regenerate-webhook-secret")
async def regenerate_webhook_secret(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_tenant = Depends(get_current_tenant),
):
    """Regenerate webhook secret for a tenant."""
    if str(tenant_id) != str(current_tenant.id):
        raise HTTPException(status_code=403, detail="Access denied")

    service = TenantService(db)
    new_secret = await service.regenerate_webhook_secret(tenant_id)
    return {"webhook_secret": new_secret, "message": "Webhook secret regenerated successfully"}
