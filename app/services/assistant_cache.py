"""Cache for pre-built assistant configurations."""
import uuid
from typing import Dict, Optional
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.models.tenant import Tenant
from app.services.skills_engine import skills_engine
from app.core.config import settings

logger = structlog.get_logger()


class AssistantCache:
    """In-memory cache for tenant assistant configurations."""

    def __init__(self):
        self._cache: Dict[str, dict] = {}
        # Map phone_number_id to tenant_id
        self._phone_to_tenant: Dict[str, str] = {}

    def set_phone_mapping(self, phone_number_id: str, tenant_id: str):
        """Map a phone number to a tenant."""
        self._phone_to_tenant[phone_number_id] = tenant_id
        logger.info("phone_mapping_cached", phone_id=phone_number_id, tenant_id=tenant_id)

    def get_tenant_by_phone(self, phone_number_id: str) -> Optional[str]:
        """Get tenant_id from phone_number_id."""
        return self._phone_to_tenant.get(phone_number_id)

    def get(self, tenant_id: str) -> Optional[dict]:
        """Get cached assistant config for tenant."""
        return self._cache.get(tenant_id)

    def set(self, tenant_id: str, assistant_config: dict):
        """Cache assistant config for tenant."""
        self._cache[tenant_id] = assistant_config
        logger.info("assistant_config_cached", tenant_id=tenant_id)

    def invalidate(self, tenant_id: str):
        """Invalidate cache for tenant."""
        if tenant_id in self._cache:
            del self._cache[tenant_id]
            logger.info("assistant_config_invalidated", tenant_id=tenant_id)

    async def warm_cache(self, db: AsyncSession):
        """Pre-load all active tenants into cache."""
        result = await db.execute(
            select(Tenant).where(
                Tenant.is_active == True,
                Tenant.deleted_at.is_(None)
            )
        )
        tenants = result.scalars().all()

        for tenant in tenants:
            try:
                assistant_config = await self._build_assistant_config(tenant)
                self.set(str(tenant.id), assistant_config)

                # Map phone number to tenant if available
                if tenant.twilio_phone_number:
                    # In production, you'd query the phone_numbers table
                    # For now, hardcode the mapping
                    pass
            except Exception as e:
                logger.error("cache_warm_failed", tenant_id=str(tenant.id), error=str(e))

        logger.info("cache_warmed", tenant_count=len(tenants))

    async def _build_assistant_config(self, tenant: Tenant) -> dict:
        """Build complete assistant configuration for tenant."""
        # Get enabled integrations
        integrations = []
        if tenant.config and isinstance(tenant.config, dict):
            tenant_integrations = tenant.config.get("integrations", {})
            if tenant_integrations.get("google_calendar", {}).get("enabled"):
                integrations.append("google_calendar")
            if tenant_integrations.get("hubspot", {}).get("enabled"):
                integrations.append("hubspot")
            if tenant_integrations.get("stripe", {}).get("enabled"):
                integrations.append("stripe")

        # Build tenant config dict
        tenant_config = {
            "business_name": tenant.business_name,
            "phone": tenant.phone,
            "timezone": tenant.timezone,
            "operating_hours": tenant.operating_hours or {},
            "services": tenant.services or [],
            "booking_rules": tenant.booking_rules or {},
        }

        # Build dynamic context (date/time will be injected at call time)
        now = datetime.now()
        dynamic_context = {
            "current_date": now.strftime("%A, %B %d, %Y"),
            "current_year": now.year,
            "current_time": now.strftime("%I:%M %p"),
            "timezone": tenant.timezone,
        }

        # Build complete system prompt with skills
        system_prompt = skills_engine.build_system_prompt(
            vertical=tenant.vertical,
            integrations=integrations,
            tenant_config=tenant_config,
            dynamic_context=dynamic_context
        )

        # Build tools
        backend_url = settings.BACKEND_URL
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "check_availability",
                    "description": "Check available time slots for a service",
                    "parameters": {
                        "type": "object",
                        "required": ["service_id", "preferred_date"],
                        "properties": {
                            "service_id": {"type": "string", "description": "ID of the service to check availability for"},
                            "preferred_date": {"type": "string", "description": "Preferred date in YYYY-MM-DD format"}
                        }
                    }
                },
                "server": {"url": f"{backend_url}/webhooks/vapi/function-call"}
            },
            {
                "type": "function",
                "function": {
                    "name": "create_booking",
                    "description": "Create a booking appointment for a customer",
                    "parameters": {
                        "type": "object",
                        "required": ["service_id", "customer_name", "customer_phone", "scheduled_datetime"],
                        "properties": {
                            "service_id": {"type": "string", "description": "ID of the service to book"},
                            "customer_name": {"type": "string", "description": "Customer's full name"},
                            "customer_phone": {"type": "string", "description": "Customer's phone number"},
                            "scheduled_datetime": {"type": "string", "description": "Appointment date and time in ISO format"},
                            "notes": {"type": "string", "description": "Additional notes from the conversation"}
                        }
                    }
                },
                "server": {"url": f"{backend_url}/webhooks/vapi/function-call"}
            },
            {
                "type": "function",
                "function": {
                    "name": "get_service_details",
                    "description": "Get details about a specific service (pricing, duration, etc.)",
                    "parameters": {
                        "type": "object",
                        "required": ["service_id"],
                        "properties": {
                            "service_id": {"type": "string", "description": "ID of the service"}
                        }
                    }
                },
                "server": {"url": f"{backend_url}/webhooks/vapi/function-call"}
            }
        ]

        # Return complete assistant configuration
        return {
            "assistant": {
                "model": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "temperature": 0.7,
                    "maxTokens": 500,
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt
                        }
                    ],
                    "tools": tools
                },
                "voice": {
                    "provider": "11labs",
                    "voiceId": "21m00Tcm4TlvDq8ikWAM",
                    "stability": 0.5,
                    "similarityBoost": 0.75
                },
                "firstMessage": f"G'day! You've reached {tenant.business_name}. How can I help you today?",
                "transcriber": {
                    "provider": "deepgram",
                    "model": "nova-2",
                    "language": "en-AU"
                },
                "responseDelaySeconds": 0.6,
                "maxDurationSeconds": 1800,
                "recordingEnabled": True,
                "serverUrl": f"{backend_url}/webhooks/vapi/function-call",
                "metadata": {
                    "tenant_id": str(tenant.id),
                    "business_name": tenant.business_name,
                    "vertical": tenant.vertical
                }
            }
        }


# Singleton instance
assistant_cache = AssistantCache()
