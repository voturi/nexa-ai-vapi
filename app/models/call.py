"""Call model."""
from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class Call(Base):
    """Call model representing a phone call."""

    __tablename__ = "calls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    # Call Details
    vapi_call_id = Column(String(255), unique=True)
    caller_phone = Column(String(20))
    caller_name = Column(String(255))

    # Status
    status = Column(String(50))  # 'ringing', 'in_progress', 'ended', 'failed'
    outcome = Column(String(50))  # 'booking_created', 'lead_qualified', 'no_answer', etc.

    # Timing
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    duration_seconds = Column(Integer)

    # Content
    transcript = Column(Text)
    recording_url = Column(String(500))
    summary = Column(Text)
    sentiment = Column(String(50))

    # Cost
    cost_cents = Column(Integer)

    # Metadata (renamed to avoid conflict with SQLAlchemy's metadata attribute)
    call_metadata = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)
