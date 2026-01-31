"""Lead model."""
from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, JSON, Date
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.core.database import Base


class Lead(Base):
    """Lead model representing a potential customer."""

    __tablename__ = "leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    call_id = Column(UUID(as_uuid=True), ForeignKey("calls.id"))

    # Contact Information
    customer_name = Column(String(255))
    customer_phone = Column(String(20), nullable=False)
    customer_email = Column(String(255))
    company_name = Column(String(255))

    # Lead Details
    lead_source = Column(String(50), default="phone_call")
    qualification_score = Column(Integer)  # 0-100
    interest_level = Column(String(50))  # 'hot', 'warm', 'cold'

    # Status
    status = Column(String(50), default="new")  # 'new', 'contacted', 'qualified', 'converted', 'lost'

    # Integration References
    crm_lead_id = Column(String(255))
    crm_contact_id = Column(String(255))

    # Context
    notes = Column(Text)
    next_followup_date = Column(Date)
    lead_metadata = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
