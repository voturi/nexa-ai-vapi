#!/usr/bin/env python3
"""
Script to configure VAPI assistant for a tenant.

Usage:
    python scripts/configure_vapi_assistant.py <tenant_id>

Example:
    python scripts/configure_vapi_assistant.py 2ad294ed-0d2c-4259-a7fd-300d7989efc8
"""
import sys
import asyncio
import uuid
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.models.tenant import Tenant
from app.integrations.vapi_client import VAPIClient
from app.services.skills_engine import skills_engine


class VAPIAssistantConfigurator:
    """Configure VAPI assistants for tenants."""

    def __init__(self):
        self.vapi_client = VAPIClient()
        self.webhook_base_url = settings.BACKEND_URL

    async def configure_assistant_for_tenant(
        self,
        tenant_id: str,
        update_existing: bool = False
    ) -> dict:
        """
        Configure VAPI assistant for a tenant.

        Args:
            tenant_id: UUID of the tenant
            update_existing: If True, update existing assistant instead of creating new

        Returns:
            Dict with assistant details
        """
        # Get database session
        async with AsyncSessionLocal() as db:
            # Load tenant
            tenant = await self._load_tenant(db, tenant_id)

            if not tenant:
                raise ValueError(f"Tenant {tenant_id} not found")

            print(f"📋 Configuring VAPI assistant for: {tenant.business_name}")
            print(f"   Vertical: {tenant.vertical}")
            print(f"   Tenant ID: {tenant.id}")

            # Get integrations
            integrations = self._get_tenant_integrations(tenant)
            print(f"   Enabled integrations: {', '.join(integrations) or 'None'}")

            # Build system prompt with skills
            system_prompt = self._build_system_prompt(tenant, integrations)
            print(f"✅ System prompt built ({len(system_prompt)} chars)")

            # Build tools definitions
            tools = self._build_tools()
            print(f"✅ Tools configured: {len(tools)} tools")

            # Build assistant configuration
            assistant_config = self._build_assistant_config(
                tenant=tenant,
                system_prompt=system_prompt,
                tools=tools
            )

            # Create or update assistant
            if update_existing and tenant.vapi_assistant_id:
                print(f"🔄 Updating existing assistant: {tenant.vapi_assistant_id}")
                assistant = await self.vapi_client.update_assistant(
                    assistant_id=tenant.vapi_assistant_id,
                    **assistant_config
                )
                assistant_id = tenant.vapi_assistant_id
            else:
                print("🚀 Creating new VAPI assistant...")
                assistant = await self.vapi_client.create_assistant(**assistant_config)
                assistant_id = assistant.get("id")

                # Update tenant with assistant ID
                from sqlalchemy import update as sql_update
                await db.execute(
                    sql_update(Tenant)
                    .where(Tenant.id == uuid.UUID(tenant_id))
                    .values(vapi_assistant_id=assistant_id)
                )
                await db.commit()

            print(f"✅ VAPI Assistant created/updated: {assistant_id}")

            # Link phone number if provided
            if tenant.twilio_phone_number:
                print(f"📞 Linking phone number: {tenant.twilio_phone_number}")
                # TODO: Implement phone number linking
                # This requires phone number provisioning via VAPI API

            print("\n" + "="*60)
            print("✅ VAPI Assistant Configuration Complete!")
            print("="*60)
            print(f"Assistant ID: {assistant_id}")
            print(f"Webhook URL: {self.webhook_base_url}/webhooks/vapi/call-started")
            print(f"Business: {tenant.business_name}")
            print(f"Phone: {tenant.twilio_phone_number or 'Not configured'}")
            print("\n📝 Next Steps:")
            print("1. Verify assistant in VAPI dashboard: https://dashboard.vapi.ai")
            print("2. Test the assistant by calling the phone number")
            print("3. Check webhook logs for call-started events")
            print("="*60)

            return {
                "assistant_id": assistant_id,
                "tenant_id": str(tenant.id),
                "business_name": tenant.business_name,
                "assistant": assistant
            }

    async def _load_tenant(self, db: AsyncSession, tenant_id: str) -> Tenant:
        """Load tenant from database."""
        try:
            tenant_uuid = uuid.UUID(tenant_id)
            result = await db.execute(
                select(Tenant).where(
                    Tenant.id == tenant_uuid,
                    Tenant.deleted_at.is_(None)
                )
            )
            return result.scalar_one_or_none()
        except ValueError:
            raise ValueError(f"Invalid tenant_id format: {tenant_id}")

    def _get_tenant_integrations(self, tenant: Tenant) -> list:
        """Get list of enabled integrations."""
        integrations = []

        if tenant.config and isinstance(tenant.config, dict):
            tenant_integrations = tenant.config.get("integrations", {})

            if tenant_integrations.get("google_calendar", {}).get("enabled"):
                integrations.append("google_calendar")
            if tenant_integrations.get("hubspot", {}).get("enabled"):
                integrations.append("hubspot")
            if tenant_integrations.get("stripe", {}).get("enabled"):
                integrations.append("stripe")

        return integrations

    def _build_system_prompt(self, tenant: Tenant, integrations: list) -> str:
        """Build system prompt using skills engine."""
        tenant_config = {
            "business_name": tenant.business_name,
            "phone": tenant.phone,
            "timezone": tenant.timezone,
            "operating_hours": tenant.operating_hours or {},
            "services": tenant.services or [],
            "booking_rules": tenant.booking_rules or {},
        }

        return skills_engine.build_system_prompt(
            vertical=tenant.vertical,
            integrations=integrations,
            tenant_config=tenant_config,
            dynamic_context=None  # Static config only during setup
        )

    def _build_tools(self) -> list:
        """Build tool definitions for the assistant."""
        webhook_url = f"{self.webhook_base_url}/webhooks/vapi/function-call"

        return [
            {
                "type": "function",
                "function": {
                    "name": "check_availability",
                    "description": "Check available time slots for a service",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "service_id": {
                                "type": "string",
                                "description": "ID of the service to check availability for"
                            },
                            "preferred_date": {
                                "type": "string",
                                "description": "Preferred date in YYYY-MM-DD format"
                            }
                        },
                        "required": ["service_id", "preferred_date"]
                    }
                },
                "server": {
                    "url": webhook_url
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_booking",
                    "description": "Create a booking appointment for a customer",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "service_id": {
                                "type": "string",
                                "description": "ID of the service to book"
                            },
                            "customer_name": {
                                "type": "string",
                                "description": "Customer's full name"
                            },
                            "customer_phone": {
                                "type": "string",
                                "description": "Customer's phone number"
                            },
                            "customer_email": {
                                "type": "string",
                                "description": "Customer's email address"
                            },
                            "scheduled_datetime": {
                                "type": "string",
                                "description": "Booking datetime in ISO format"
                            },
                            "notes": {
                                "type": "string",
                                "description": "Additional notes or requirements"
                            }
                        },
                        "required": ["service_id", "customer_name", "customer_phone", "scheduled_datetime"]
                    }
                },
                "server": {
                    "url": webhook_url
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_lead",
                    "description": "Capture a lead when customer is not ready to book",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "customer_name": {
                                "type": "string",
                                "description": "Customer's name"
                            },
                            "customer_phone": {
                                "type": "string",
                                "description": "Customer's phone number"
                            },
                            "customer_email": {
                                "type": "string",
                                "description": "Customer's email address"
                            },
                            "interest": {
                                "type": "string",
                                "description": "What service or product they're interested in"
                            },
                            "notes": {
                                "type": "string",
                                "description": "Additional notes from the conversation"
                            }
                        },
                        "required": ["customer_name", "customer_phone"]
                    }
                },
                "server": {
                    "url": webhook_url
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_service_details",
                    "description": "Get details about a specific service (pricing, duration, etc.)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "service_id": {
                                "type": "string",
                                "description": "ID of the service"
                            }
                        },
                        "required": ["service_id"]
                    }
                },
                "server": {
                    "url": webhook_url
                }
            }
        ]

    def _build_assistant_config(
        self,
        tenant: Tenant,
        system_prompt: str,
        tools: list
    ) -> dict:
        """Build assistant configuration."""
        # Get first message from tenant config or use default
        ai_behavior = tenant.ai_behavior or {}
        first_message = ai_behavior.get(
            "first_message",
            f"G'day! You've reached {tenant.business_name}. How can I help you today?"
        )

        # Build voice config
        voice_id = ai_behavior.get("voice_id", "21m00Tcm4TlvDq8ikWAM")  # Default ElevenLabs voice
        voice = self.vapi_client.build_voice_config(
            provider="11labs",
            voice_id=voice_id,
            stability=0.5,
            similarity_boost=0.75
        )

        # Build model config with system prompt and tools
        model = self.vapi_client.build_model_config(
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.7,
            max_tokens=250,
            system_prompt=system_prompt,
            tools=tools
        )

        # Build metadata
        metadata = {
            "tenant_id": str(tenant.id),
            "vertical": tenant.vertical,
            "business_name": tenant.business_name
        }

        # Webhook configuration
        server_url = f"{self.webhook_base_url}/webhooks/vapi/call-started"

        # Truncate name to fit VAPI's 40 character limit
        assistant_name = tenant.business_name[:35] if len(tenant.business_name) <= 35 else tenant.business_name[:35]

        return {
            "name": assistant_name,
            "model": model,
            "voice": voice,
            "first_message": first_message,
            "metadata": metadata,
            "server_url": server_url,
            "server_url_secret": tenant.webhook_secret,
        }


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/configure_vapi_assistant.py <tenant_id>")
        print("\nExample:")
        print("  python scripts/configure_vapi_assistant.py 2ad294ed-0d2c-4259-a7fd-300d7989efc8")
        sys.exit(1)

    tenant_id = sys.argv[1]
    update_existing = "--update" in sys.argv

    print("\n" + "="*60)
    print("🤖 VAPI Assistant Configurator")
    print("="*60 + "\n")

    configurator = VAPIAssistantConfigurator()

    try:
        result = await configurator.configure_assistant_for_tenant(
            tenant_id=tenant_id,
            update_existing=update_existing
        )
        print("\n✨ Configuration successful!")
    except Exception as e:
        print(f"\n❌ Configuration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
