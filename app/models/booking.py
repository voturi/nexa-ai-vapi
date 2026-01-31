"""Booking model."""
from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.core.database import Base


class Booking(Base):
    """Booking model representing a scheduled appointment."""

    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    call_id = Column(UUID(as_uuid=True), ForeignKey("calls.id"))

    # Customer Information
    customer_name = Column(String(255), nullable=False)
    customer_phone = Column(String(20), nullable=False)
    customer_email = Column(String(255))

    # Service Details
    service_id = Column(String(100), nullable=False)
    service_name = Column(String(255))

    # Scheduling
    scheduled_at = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    timezone = Column(String(50))

    # Status
    status = Column(String(50), default="confirmed")  # 'confirmed', 'cancelled', 'completed', 'no_show'
    cancellation_reason = Column(Text)

    # Integration References
    calendar_event_id = Column(String(255))
    crm_contact_id = Column(String(255))

    # Additional Info
    notes = Column(Text)
    booking_metadata = Column(JSON)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    cancelled_at = Column(DateTime)
