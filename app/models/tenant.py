"""Tenant model."""
from sqlalchemy import Column, String, DateTime, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.core.database import Base


class Tenant(Base):
    """Tenant model representing a business using the voice AI service."""

    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Business Information
    business_name = Column(String(255), nullable=False)
    vertical = Column(String(50), nullable=False)  # 'tradies', 'hair_salon', etc.
    phone = Column(String(20))
    email = Column(String(255))
    address = Column(String)
    timezone = Column(String(50), default="Australia/Sydney")

    # Configuration
    config = Column(JSON, nullable=False, default=dict)
    operating_hours = Column(JSON)
    services = Column(JSON)
    booking_rules = Column(JSON)
    ai_behavior = Column(JSON)

    # Integration IDs
    vapi_assistant_id = Column(String(255), unique=True)
    twilio_number_sid = Column(String(255))
    twilio_phone_number = Column(String(20))

    # Security
    api_key = Column(String(255), unique=True, nullable=False)
    webhook_secret = Column(String(255), nullable=False)

    # Subscription
    subscription_tier = Column(String(50), default="basic")
    subscription_status = Column(String(50), default="active")

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
