"""Call API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.core.auth import get_current_user_tenant as get_current_tenant
from app.schemas.call import CallResponse
from app.services.call_service import CallService

router = APIRouter()


@router.get("", response_model=List[CallResponse])
async def list_calls(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_tenant = Depends(get_current_tenant),
):
    """List calls for current tenant."""
    service = CallService(db)
    return await service.list_by_tenant(
        tenant_id=current_tenant.id,
        skip=skip,
        limit=limit,
        status=status
    )


@router.get("/{call_id}", response_model=CallResponse)
async def get_call(
    call_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_tenant = Depends(get_current_tenant),
):
    """Get call by ID."""
    service = CallService(db)
    call = await service.get_by_id(call_id)

    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    if str(call.tenant_id) != str(current_tenant.id):
        raise HTTPException(status_code=403, detail="Access denied")

    return call
