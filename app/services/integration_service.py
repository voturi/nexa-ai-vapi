"""Integration service for managing tenant integration credentials."""
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import credentials_manager
from app.models.integration import TenantIntegration

logger = structlog.get_logger()


class IntegrationService:
    """Service for managing tenant integration credentials."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_integration(
        self,
        tenant_id: UUID,
        integration_type: str,
    ) -> Optional[TenantIntegration]:
        """Get a tenant's integration record."""
        result = await self.db.execute(
            select(TenantIntegration).where(
                TenantIntegration.tenant_id == tenant_id,
                TenantIntegration.integration_type == integration_type,
                TenantIntegration.status != "deleted",
            )
        )
        return result.scalar_one_or_none()

    async def get_credentials(
        self,
        tenant_id: UUID,
        integration_type: str,
    ) -> Optional[Dict[str, Any]]:
        """Get decrypted credentials for a tenant integration."""
        integration = await self.get_integration(tenant_id, integration_type)
        if not integration:
            return None

        try:
            return credentials_manager.decrypt(integration.encrypted_credentials)
        except Exception as e:
            logger.error(
                "credential_decryption_failed",
                tenant_id=str(tenant_id),
                integration_type=integration_type,
                error=str(e),
            )
            return None

    async def store_credentials(
        self,
        tenant_id: UUID,
        integration_type: str,
        credentials_data: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
        integration_name: Optional[str] = None,
    ) -> TenantIntegration:
        """
        Encrypt and store credentials for a tenant integration.

        If an integration record already exists, update it. Otherwise create new.
        """
        encrypted = credentials_manager.encrypt(credentials_data)

        existing = await self.get_integration(tenant_id, integration_type)

        if existing:
            existing.encrypted_credentials = encrypted
            existing.encryption_key_id = "default"
            existing.status = "active"
            existing.last_error = None
            existing.updated_at = datetime.utcnow()
            if config:
                existing.config = config
            if integration_name:
                existing.integration_name = integration_name
            await self.db.commit()
            await self.db.refresh(existing)

            logger.info(
                "integration_credentials_updated",
                tenant_id=str(tenant_id),
                integration_type=integration_type,
            )
            return existing

        integration = TenantIntegration(
            tenant_id=tenant_id,
            integration_type=integration_type,
            integration_name=integration_name or integration_type,
            encrypted_credentials=encrypted,
            encryption_key_id="default",
            config=config or {},
            status="active",
        )
        self.db.add(integration)
        await self.db.commit()
        await self.db.refresh(integration)

        logger.info(
            "integration_credentials_stored",
            tenant_id=str(tenant_id),
            integration_type=integration_type,
            integration_id=str(integration.id),
        )
        return integration

    async def update_credentials(
        self,
        tenant_id: UUID,
        integration_type: str,
        credentials_data: Dict[str, Any],
    ) -> Optional[TenantIntegration]:
        """Update only the credentials for an existing integration."""
        integration = await self.get_integration(tenant_id, integration_type)
        if not integration:
            return None

        integration.encrypted_credentials = credentials_manager.encrypt(credentials_data)
        integration.updated_at = datetime.utcnow()
        integration.last_error = None
        await self.db.commit()
        await self.db.refresh(integration)
        return integration

    async def update_config(
        self,
        tenant_id: UUID,
        integration_type: str,
        config: Dict[str, Any],
    ) -> Optional[TenantIntegration]:
        """Update the config JSON for an existing integration."""
        integration = await self.get_integration(tenant_id, integration_type)
        if not integration:
            return None

        integration.config = config
        integration.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(integration)
        return integration

    async def disconnect(
        self,
        tenant_id: UUID,
        integration_type: str,
    ) -> bool:
        """Soft-delete an integration (mark as deleted)."""
        integration = await self.get_integration(tenant_id, integration_type)
        if not integration:
            return False

        integration.status = "deleted"
        integration.updated_at = datetime.utcnow()
        await self.db.commit()

        logger.info(
            "integration_disconnected",
            tenant_id=str(tenant_id),
            integration_type=integration_type,
        )
        return True

    async def record_error(
        self,
        tenant_id: UUID,
        integration_type: str,
        error_message: str,
    ) -> None:
        """Record an error on an integration (e.g. token revoked)."""
        integration = await self.get_integration(tenant_id, integration_type)
        if integration:
            integration.last_error = error_message
            integration.updated_at = datetime.utcnow()
            await self.db.commit()

    async def record_sync(
        self,
        tenant_id: UUID,
        integration_type: str,
    ) -> None:
        """Record a successful sync timestamp."""
        integration = await self.get_integration(tenant_id, integration_type)
        if integration:
            integration.last_sync_at = datetime.utcnow()
            integration.last_error = None
            await self.db.commit()
