"""VAPI service for handling VAPI webhooks and API calls."""
from sqlalchemy.ext.asyncio import AsyncSession


class VAPIService:
    """Service for VAPI operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def handle_call_started(self, data: dict) -> dict:
        """Handle call started webhook."""
        # TODO: Implement
        # Load tenant config
        # Build system prompt with skills
        # Return enhanced context
        return {
            "message": {
                "role": "system",
                "content": "You are an AI receptionist."
            }
        }

    async def handle_function_call(self, data: dict):
        """Handle function call webhook."""
        # TODO: Implement
        # Extract tenant_id
        # Route to appropriate integration
        return {"success": True}
