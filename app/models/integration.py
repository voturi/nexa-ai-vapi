"""Integration model."""
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.core.database import Base


class TenantIntegration(Base):
    """Tenant integration model for storing encrypted credentials."""

    __tablename__ = "tenant_integrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    # Integration Details
    integration_type = Column(String(50), nullable=False)  # 'google_calendar', 'hubspot', etc.
    integration_name = Column(String(100))

    # Encrypted Credentials
    encrypted_credentials = Column(LargeBinary, nullable=False)
    encryption_key_id = Column(String(100), nullable=False)

    # Configuration
    config = Column(JSON)

    # Status
    status = Column(String(50), default="active")
    last_sync_at = Column(DateTime)
    last_error = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
