"""Booking API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_tenant
from app.schemas.booking import BookingCreate, BookingUpdate, BookingResponse
from app.services.booking_service import BookingService

router = APIRouter()


@router.get("", response_model=List[BookingResponse])
async def list_bookings(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_tenant = Depends(get_current_tenant),
):
    """List bookings for current tenant."""
    service = BookingService(db)
    return await service.list_by_tenant(
        tenant_id=current_tenant.id,
        skip=skip,
        limit=limit
    )


@router.post("", response_model=BookingResponse)
async def create_booking(
    booking_data: BookingCreate,
    db: AsyncSession = Depends(get_db),
    current_tenant = Depends(get_current_tenant),
):
    """Create a booking manually."""
    service = BookingService(db)
    return await service.create(tenant_id=current_tenant.id, booking_data=booking_data)


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_tenant = Depends(get_current_tenant),
):
    """Get booking by ID."""
    service = BookingService(db)
    booking = await service.get_by_id(booking_id)

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if str(booking.tenant_id) != str(current_tenant.id):
        raise HTTPException(status_code=403, detail="Access denied")

    return booking


@router.put("/{booking_id}", response_model=BookingResponse)
async def update_booking(
    booking_id: UUID,
    booking_data: BookingUpdate,
    db: AsyncSession = Depends(get_db),
    current_tenant = Depends(get_current_tenant),
):
    """Update booking."""
    service = BookingService(db)
    booking = await service.get_by_id(booking_id)

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if str(booking.tenant_id) != str(current_tenant.id):
        raise HTTPException(status_code=403, detail="Access denied")

    return await service.update(booking_id, booking_data)


@router.delete("/{booking_id}")
async def cancel_booking(
    booking_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_tenant = Depends(get_current_tenant),
):
    """Cancel booking."""
    service = BookingService(db)
    booking = await service.get_by_id(booking_id)

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if str(booking.tenant_id) != str(current_tenant.id):
        raise HTTPException(status_code=403, detail="Access denied")

    await service.cancel(booking_id)
    return {"message": "Booking cancelled successfully"}
