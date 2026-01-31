"""Booking schemas."""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class BookingBase(BaseModel):
    """Base booking schema."""
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None
    service_id: str
    service_name: Optional[str] = None
    scheduled_at: datetime
    duration_minutes: int
    notes: Optional[str] = None


class BookingCreate(BookingBase):
    """Schema for creating a booking."""
    pass


class BookingUpdate(BaseModel):
    """Schema for updating a booking."""
    scheduled_at: Optional[datetime] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class BookingResponse(BookingBase):
    """Schema for booking response."""
    id: UUID
    tenant_id: UUID
    call_id: Optional[UUID] = None
    status: str
    calendar_event_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
