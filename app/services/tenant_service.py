"""Tenant service - business logic for tenant operations."""
import secrets
import uuid
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, update as sql_update, delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantUpdate, TenantResponse


class TenantService:
    """Service for tenant operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _generate_api_key() -> str:
        """Generate a secure API key for tenant authentication."""
        return f"sk_{secrets.token_urlsafe(32)}"

    @staticmethod
    def _generate_webhook_secret() -> str:
        """Generate a webhook secret for VAPI signature verification."""
        return secrets.token_urlsafe(32)

    async def create(self, tenant_data: TenantCreate) -> Tenant:
        """
        Create a new tenant.

        Steps:
        1. Generate API key and webhook secret
        2. Create tenant record in database
        3. Optionally provision VAPI assistant
        4. Optionally provision Twilio number
        """
        # Create tenant with generated credentials and structured fields
        tenant = Tenant(
            id=uuid.uuid4(),
            business_name=tenant_data.business_name,
            vertical=tenant_data.vertical,
            phone=tenant_data.phone,
            email=tenant_data.email,
            timezone=tenant_data.timezone,
            config=tenant_data.config,
            operating_hours=tenant_data.operating_hours,
            services=tenant_data.services,
            booking_rules=tenant_data.booking_rules,
            ai_behavior=tenant_data.ai_behavior,
            api_key=self._generate_api_key(),
            webhook_secret=self._generate_webhook_secret(),
            subscription_tier="basic",
            subscription_status="active",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.db.add(tenant)
        await self.db.commit()
        await self.db.refresh(tenant)

        # TODO: Provision VAPI assistant
        # tenant.vapi_assistant_id = await self._create_vapi_assistant(tenant)

        # TODO: Provision Twilio number
        # tenant.twilio_phone_number = await self._provision_twilio_number(tenant)

        return tenant

    async def get_by_id(self, tenant_id: uuid.UUID) -> Optional[Tenant]:
        """Get tenant by ID."""
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id, Tenant.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_api_key(api_key: str) -> Optional[Tenant]:
        """
        Get tenant by API key (for authentication).

        Note: This is a static method because it's called from the security
        dependency before we have a database session.
        """
        # TODO: This needs to be implemented with a database session
        # For now, return None - will be fixed when we inject DB properly
        return None

    async def get_by_api_key_with_db(self, api_key: str) -> Optional[Tenant]:
        """Get tenant by API key (database-backed version)."""
        result = await self.db.execute(
            select(Tenant).where(
                Tenant.api_key == api_key,
                Tenant.is_active == True,
                Tenant.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def update(self, tenant_id: uuid.UUID, tenant_data: TenantUpdate) -> Tenant:
        """Update tenant information."""
        # Get existing tenant
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        # Update fields if provided
        update_data = tenant_data.model_dump(exclude_unset=True)
        update_data['updated_at'] = datetime.utcnow()

        await self.db.execute(
            sql_update(Tenant)
            .where(Tenant.id == tenant_id)
            .values(**update_data)
        )

        await self.db.commit()

        # Refresh to get updated data
        await self.db.refresh(tenant)
        return tenant

    async def delete(self, tenant_id: uuid.UUID) -> None:
        """
        Soft delete a tenant.

        Sets deleted_at timestamp and deactivates the tenant.
        """
        await self.db.execute(
            sql_update(Tenant)
            .where(Tenant.id == tenant_id)
            .values(
                deleted_at=datetime.utcnow(),
                is_active=False,
                updated_at=datetime.utcnow()
            )
        )
        await self.db.commit()

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False
    ) -> List[Tenant]:
        """List all tenants with pagination."""
        query = select(Tenant).where(Tenant.deleted_at.is_(None))

        if not include_inactive:
            query = query.where(Tenant.is_active == True)

        query = query.offset(skip).limit(limit).order_by(Tenant.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count(self, include_inactive: bool = False) -> int:
        """Count total tenants."""
        from sqlalchemy import func

        query = select(func.count(Tenant.id)).where(Tenant.deleted_at.is_(None))

        if not include_inactive:
            query = query.where(Tenant.is_active == True)

        result = await self.db.execute(query)
        return result.scalar_one()

    async def regenerate_api_key(self, tenant_id: uuid.UUID) -> str:
        """Regenerate API key for a tenant (in case of key compromise)."""
        new_api_key = self._generate_api_key()

        await self.db.execute(
            sql_update(Tenant)
            .where(Tenant.id == tenant_id)
            .values(api_key=new_api_key, updated_at=datetime.utcnow())
        )

        await self.db.commit()
        return new_api_key

    async def regenerate_webhook_secret(self, tenant_id: uuid.UUID) -> str:
        """Regenerate webhook secret for a tenant."""
        new_secret = self._generate_webhook_secret()

        await self.db.execute(
            sql_update(Tenant)
            .where(Tenant.id == tenant_id)
            .values(webhook_secret=new_secret, updated_at=datetime.utcnow())
        )

        await self.db.commit()
        return new_secret

    async def update_vapi_assistant_id(
        self,
        tenant_id: uuid.UUID,
        assistant_id: str
    ) -> None:
        """Update VAPI assistant ID after provisioning."""
        await self.db.execute(
            sql_update(Tenant)
            .where(Tenant.id == tenant_id)
            .values(vapi_assistant_id=assistant_id, updated_at=datetime.utcnow())
        )
        await self.db.commit()

    async def update_twilio_number(
        self,
        tenant_id: uuid.UUID,
        phone_number: str,
        number_sid: str
    ) -> None:
        """Update Twilio phone number after provisioning."""
        await self.db.execute(
            sql_update(Tenant)
            .where(Tenant.id == tenant_id)
            .values(
                twilio_phone_number=phone_number,
                twilio_number_sid=number_sid,
                updated_at=datetime.utcnow()
            )
        )
        await self.db.commit()

    # TODO: Implement VAPI assistant provisioning
    # async def _create_vapi_assistant(self, tenant: Tenant) -> str:
    #     """
    #     Create a VAPI assistant for this tenant.
    #
    #     Returns the assistant ID.
    #     """
    #     pass

    # TODO: Implement Twilio number provisioning
    # async def _provision_twilio_number(self, tenant: Tenant) -> str:
    #     """
    #     Provision a Twilio phone number for this tenant.
    #
    #     Returns the phone number.
    #     """
    #     pass
