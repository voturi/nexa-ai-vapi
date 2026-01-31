"""Lead schemas."""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
from uuid import UUID


class LeadUpdate(BaseModel):
    """Schema for updating a lead."""
    status: Optional[str] = None
    qualification_score: Optional[int] = None
    interest_level: Optional[str] = None
    notes: Optional[str] = None
    next_followup_date: Optional[date] = None


class LeadResponse(BaseModel):
    """Schema for lead response."""
    id: UUID
    tenant_id: UUID
    call_id: Optional[UUID] = None
    customer_name: Optional[str] = None
    customer_phone: str
    customer_email: Optional[str] = None
    lead_source: str
    qualification_score: Optional[int] = None
    interest_level: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
