"""VAPI service for handling VAPI webhooks and API calls."""
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.models.tenant import Tenant
from app.services.skills_engine import skills_engine

logger = structlog.get_logger()


class VAPIService:
    """Service for VAPI operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_tenant_by_id(self, tenant_id: str) -> Optional[Tenant]:
        """Load tenant from database."""
        try:
            tenant_uuid = uuid.UUID(tenant_id)
            result = await self.db.execute(
                select(Tenant).where(
                    Tenant.id == tenant_uuid,
                    Tenant.is_active == True,
                    Tenant.deleted_at.is_(None)
                )
            )
            return result.scalar_one_or_none()
        except (ValueError, Exception) as e:
            logger.error("failed_to_load_tenant", tenant_id=tenant_id, error=str(e))
            return None

    async def _get_tenant_integrations(self, tenant: Tenant) -> list:
        """Get list of enabled integrations for tenant."""
        integrations = []

        # Check which integrations are enabled in tenant config
        if tenant.config and isinstance(tenant.config, dict):
            tenant_integrations = tenant.config.get("integrations", {})

            if tenant_integrations.get("google_calendar", {}).get("enabled"):
                integrations.append("google_calendar")
            if tenant_integrations.get("hubspot", {}).get("enabled"):
                integrations.append("hubspot")
            if tenant_integrations.get("stripe", {}).get("enabled"):
                integrations.append("stripe")

        return integrations

    def _get_backend_url(self) -> str:
        """Get backend URL for webhooks."""
        from app.core.config import settings
        return settings.BACKEND_URL

    def _build_tools(self) -> list:
        """Build tool definitions for VAPI."""
        backend_url = self._get_backend_url()

        return [
            {
                "type": "function",
                "function": {
                    "name": "check_availability",
                    "description": "Check available time slots for a service",
                    "parameters": {
                        "type": "object",
                        "required": ["service_id", "preferred_date"],
                        "properties": {
                            "service_id": {
                                "type": "string",
                                "description": "ID of the service to check availability for"
                            },
                            "preferred_date": {
                                "type": "string",
                                "description": "Preferred date in YYYY-MM-DD format"
                            }
                        }
                    }
                },
                "server": {
                    "url": f"{backend_url}/webhooks/vapi/function-call"
                }
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
                        }
                    }
                },
                "server": {
                    "url": f"{backend_url}/webhooks/vapi/function-call"
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_lead",
                    "description": "Capture a lead when customer is not ready to book",
                    "parameters": {
                        "type": "object",
                        "required": ["customer_name", "customer_phone"],
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
                        }
                    }
                },
                "server": {
                    "url": f"{backend_url}/webhooks/vapi/function-call"
                }
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
                            "service_id": {
                                "type": "string",
                                "description": "ID of the service"
                            }
                        }
                    }
                },
                "server": {
                    "url": f"{backend_url}/webhooks/vapi/function-call"
                }
            }
        ]

    async def _build_dynamic_context(self, tenant: Tenant) -> Dict[str, Any]:
        """Build real-time dynamic context for the call."""
        now = datetime.now()
        context = {
            "current_date": now.strftime("%A, %B %d, %Y"),  # e.g., "Saturday, February 01, 2026"
            "current_year": now.year,
            "current_time": now.strftime("%I:%M %p"),  # e.g., "02:44 PM"
            "timezone": tenant.timezone,
        }

        # TODO: Add availability check from calendar
        # TODO: Add caller history lookup
        # TODO: Add business status (open/closed)

        return context

    async def handle_call_started(self, data: dict, tenant_id: Optional[str] = None) -> dict:
        """
        Handle call started webhook from VAPI.

        This is where we inject dynamic context and tenant-specific prompts.

        Args:
            data: Webhook payload from VAPI containing call metadata
            tenant_id: Optional tenant_id if already extracted by webhook handler

        Returns:
            Response with system prompt and configuration for VAPI
        """
        # Use provided tenant_id or extract from metadata
        if not tenant_id:
            tenant_id = data.get("call", {}).get("metadata", {}).get("tenant_id")

        if not tenant_id:
            logger.error("call_started_missing_tenant_id", data=data)
            return {
                "error": "Missing tenant_id in metadata"
            }

        # Load tenant configuration
        tenant = await self._get_tenant_by_id(tenant_id)

        if not tenant:
            logger.error("call_started_tenant_not_found", tenant_id=tenant_id)
            return {
                "error": f"Tenant {tenant_id} not found"
            }

        logger.info(
            "call_started",
            tenant_id=str(tenant.id),
            business_name=tenant.business_name,
            vertical=tenant.vertical,
            call_id=data.get("call", {}).get("id")
        )

        # Get enabled integrations
        integrations = await self._get_tenant_integrations(tenant)

        # Build tenant config dict
        tenant_config = {
            "business_name": tenant.business_name,
            "phone": tenant.phone,
            "timezone": tenant.timezone,
            "operating_hours": tenant.operating_hours or {},
            "services": tenant.services or [],
            "booking_rules": tenant.booking_rules or {},
        }

        # Build dynamic context
        dynamic_context = await self._build_dynamic_context(tenant)

        # Build complete system prompt with skills
        system_prompt = skills_engine.build_system_prompt(
            vertical=tenant.vertical,
            integrations=integrations,
            tenant_config=tenant_config,
            dynamic_context=dynamic_context
        )

        # Build complete assistant configuration for assistant-request
        # This returns the FULL assistant config dynamically
        response = {
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
                    "tools": self._build_tools()
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
                "serverUrl": f"{self._get_backend_url()}/webhooks/vapi/function-call",
                "metadata": {
                    "tenant_id": str(tenant.id),
                    "business_name": tenant.business_name,
                    "vertical": tenant.vertical
                }
            }
        }

        logger.info(
            "call_started_response_prepared",
            tenant_id=str(tenant.id),
            response_has_assistant=("assistant" in response),
            system_prompt_length=len(system_prompt),
            tools_count=len(response["assistant"]["model"]["tools"])
        )

        return response

    async def handle_function_call(self, data: dict, tenant_id: str) -> Dict[str, Any]:
        """
        Handle function call webhook from VAPI.

        This is triggered when the AI calls a tool/function.
        We execute the integration action with tenant-specific credentials.

        Args:
            data: Webhook payload containing function name, parameters, and call metadata
            tenant_id: Tenant ID extracted from webhook payload

        Returns:
            Result of the function execution
        """
        # Tenant ID is passed from the webhook handler
        if not tenant_id:
            logger.error("function_call_missing_tenant_id", data=data)
            return {
                "error": "Missing tenant_id in metadata"
            }

        # Extract function details from VAPI's toolCallList structure
        message = data.get("message", {})
        tool_call_list = message.get("toolCallList", [])

        if not tool_call_list or len(tool_call_list) == 0:
            logger.error("no_tool_calls_in_message", tenant_id=tenant_id)
            return {
                "results": [{
                    "result": "Error: No tool calls found in message"
                }]
            }

        # Get the first tool call
        first_tool_call = tool_call_list[0]
        tool_call_id = first_tool_call.get("id")
        function_data = first_tool_call.get("function", {})
        function_name = function_data.get("name")
        arguments = function_data.get("arguments", {})

        # Parse arguments if they're a JSON string
        if isinstance(arguments, str):
            import json
            try:
                parameters = json.loads(arguments)
            except:
                parameters = {}
        else:
            parameters = arguments

        logger.info(
            "function_call_received",
            tenant_id=tenant_id,
            tool_call_id=tool_call_id,
            function_name=function_name,
            parameters=parameters
        )

        # Load tenant
        tenant = await self._get_tenant_by_id(tenant_id)

        if not tenant:
            logger.error("function_call_tenant_not_found", tenant_id=tenant_id)
            return {
                "error": f"Tenant {tenant_id} not found"
            }

        # Route to appropriate integration handler
        try:
            if function_name == "check_availability":
                result = await self._handle_check_availability(tenant, parameters)
            elif function_name == "create_booking":
                result = await self._handle_create_booking(tenant, parameters)
            elif function_name == "create_lead":
                result = await self._handle_create_lead(tenant, parameters)
            elif function_name == "get_service_details":
                result = await self._handle_get_service_details(tenant, parameters)
            else:
                logger.error("unknown_function_call", function_name=function_name)
                result = {
                    "error": f"Unknown function: {function_name}"
                }

            logger.info(
                "function_call_completed",
                tenant_id=tenant_id,
                function_name=function_name,
                tool_call_id=tool_call_id,
                success=True
            )

            # Return in VAPI's expected format
            # Convert result to string format for VAPI
            if isinstance(result, dict):
                result_str = result.get("message", str(result))
            else:
                result_str = str(result)

            return {
                "results": [{
                    "toolCallId": tool_call_id,
                    "result": result_str
                }]
            }

        except Exception as e:
            logger.error(
                "function_call_failed",
                tenant_id=tenant_id,
                function_name=function_name,
                error=str(e)
            )
            # Return error in VAPI's expected format
            return {
                "results": [{
                    "toolCallId": tool_call_id if 'tool_call_id' in locals() else "unknown",
                    "result": f"Error: {str(e)}"
                }]
            }

    async def _handle_check_availability(
        self,
        tenant: Tenant,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle check_availability tool call."""
        # TODO: Implement calendar integration
        # For now, return mock data with realistic dates
        from datetime import datetime, timedelta

        service_id = parameters.get("service_id")
        preferred_date = parameters.get("preferred_date")

        logger.info(
            "check_availability",
            tenant_id=str(tenant.id),
            service_id=service_id,
            preferred_date=preferred_date
        )

        # Parse the requested date or use tomorrow as default
        try:
            if preferred_date:
                # Try to parse the date
                request_date = datetime.strptime(preferred_date, "%Y-%m-%d")
                # If the date is in the past or before 2026, use current date + 1
                if request_date.year < 2026 or request_date < datetime.now():
                    base_date = datetime.now() + timedelta(days=1)
                else:
                    base_date = request_date
            else:
                # Default to tomorrow
                base_date = datetime.now() + timedelta(days=1)
        except:
            # If parsing fails, use tomorrow
            base_date = datetime.now() + timedelta(days=1)

        # Generate realistic time slots for the requested date
        available_slots = [
            {
                "datetime": f"{base_date.strftime('%Y-%m-%d')}T09:00:00",
                "available": True,
                "slot": "9:00 AM"
            },
            {
                "datetime": f"{base_date.strftime('%Y-%m-%d')}T11:00:00",
                "available": True,
                "slot": "11:00 AM"
            },
            {
                "datetime": f"{base_date.strftime('%Y-%m-%d')}T14:00:00",
                "available": True,
                "slot": "2:00 PM"
            },
            {
                "datetime": f"{base_date.strftime('%Y-%m-%d')}T16:00:00",
                "available": True,
                "slot": "4:00 PM"
            },
        ]

        # Format the date very clearly
        date_formatted = base_date.strftime('%A, %B %d, %Y')

        # Create time list for speaking
        time_list = ', '.join([slot['slot'] for slot in available_slots])

        # Return a simple string that the AI can directly speak
        # This is the format that works best with VAPI
        return f"We have {len(available_slots)} available appointments on {date_formatted}. The available times are: {time_list}. Which time works best for you?"

    async def _handle_create_booking(
        self,
        tenant: Tenant,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle create_booking tool call."""
        # TODO: Implement actual booking creation
        from datetime import datetime

        logger.info(
            "create_booking",
            tenant_id=str(tenant.id),
            parameters=parameters
        )

        # Extract booking details
        customer_name = parameters.get("customer_name", "Customer")
        customer_phone = parameters.get("customer_phone", "")
        service_id = parameters.get("service_id", "")
        scheduled_datetime = parameters.get("scheduled_datetime", "")
        notes = parameters.get("notes", "")

        # Parse and format the scheduled time
        try:
            if scheduled_datetime:
                dt = datetime.fromisoformat(scheduled_datetime.replace('Z', '+00:00'))
                # If year is wrong, fix it to 2026
                if dt.year < 2026:
                    dt = dt.replace(year=2026)
                formatted_time = dt.strftime("%A, %B %d, %Y at %I:%M %p")
            else:
                formatted_time = "scheduled time"
        except:
            formatted_time = "scheduled time"

        booking_id = f"booking_{uuid.uuid4().hex[:8]}"

        # Return a simple string response
        return f"Perfect! I've confirmed your booking for {formatted_time}. Your booking reference is {booking_id}. We'll send you a confirmation SMS shortly."

    async def _handle_create_lead(
        self,
        tenant: Tenant,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle create_lead tool call."""
        # TODO: Implement lead creation and CRM sync
        logger.info(
            "create_lead",
            tenant_id=str(tenant.id),
            parameters=parameters
        )

        customer_name = parameters.get("customer_name", "Customer")
        interest = parameters.get("interest", "")
        lead_id = f"lead_{uuid.uuid4().hex[:8]}"

        # Return a simple string response
        return f"Thanks {customer_name}! I've captured your details and someone from our team will call you back within 24 hours to discuss your {interest or 'inquiry'}."

    async def _handle_get_service_details(
        self,
        tenant: Tenant,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle get_service_details tool call."""
        service_id = parameters.get("service_id")

        logger.info(
            "get_service_details",
            tenant_id=str(tenant.id),
            service_id=service_id
        )

        # Get service from tenant config
        services = tenant.services or []
        service = next(
            (s for s in services if s.get("id") == service_id),
            None
        )

        if service:
            # Format a nice description
            service_name = service.get("name", "Service")
            duration = service.get("duration_minutes", 60)
            price = service.get("price", "Price on request")
            description = service.get("description", "")

            # Return a simple string response
            return f"{service_name} takes approximately {duration} minutes and costs {price}. {description}"
        else:
            # Return a generic response if service not found
            return "I don't have details for that specific service. Let me connect you with someone who can help with pricing."
