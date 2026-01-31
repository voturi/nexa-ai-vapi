"""Call schemas."""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class CallResponse(BaseModel):
    """Schema for call response."""
    id: UUID
    tenant_id: UUID
    vapi_call_id: Optional[str] = None
    caller_phone: Optional[str] = None
    caller_name: Optional[str] = None
    status: Optional[str] = None
    outcome: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    transcript: Optional[str] = None
    recording_url: Optional[str] = None
    summary: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
