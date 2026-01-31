"""Tenant schemas."""
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID


class TenantBase(BaseModel):
    """Base tenant schema."""
    business_name: str
    vertical: str
    phone: Optional[str] = None
    email: Optional[str] = None
    timezone: str = "Australia/Sydney"


class TenantCreate(TenantBase):
    """Schema for creating a tenant."""
    config: Dict[str, Any] = {}
    operating_hours: Optional[Dict[str, Any]] = None
    services: Optional[List[Dict[str, Any]]] = None
    booking_rules: Optional[Dict[str, Any]] = None
    ai_behavior: Optional[Dict[str, Any]] = None


class TenantUpdate(BaseModel):
    """Schema for updating a tenant."""
    business_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    operating_hours: Optional[Dict[str, Any]] = None
    services: Optional[List[Dict[str, Any]]] = None
    booking_rules: Optional[Dict[str, Any]] = None
    ai_behavior: Optional[Dict[str, Any]] = None


class TenantResponse(TenantBase):
    """Schema for tenant response."""
    id: UUID
    api_key: str
    vapi_assistant_id: Optional[str] = None
    twilio_phone_number: Optional[str] = None
    subscription_tier: str
    subscription_status: str
    created_at: datetime

    # Include the structured fields in response
    operating_hours: Optional[Dict[str, Any]] = None
    services: Optional[List[Dict[str, Any]]] = None
    booking_rules: Optional[Dict[str, Any]] = None
    ai_behavior: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
