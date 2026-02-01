"""VAPI API Client for programmatic assistant management."""
import httpx
from typing import Dict, List, Optional, Any
from app.core.config import settings


class VAPIClient:
    """Client for VAPI API operations."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize VAPI client."""
        self.api_key = api_key or settings.VAPI_API_KEY
        self.base_url = settings.VAPI_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def create_assistant(
        self,
        name: str,
        model: Dict[str, Any],
        voice: Dict[str, Any],
        first_message: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        server_url: Optional[str] = None,
        server_url_secret: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new VAPI assistant.

        Args:
            name: Assistant name
            model: Model configuration (provider, model, etc.)
            voice: Voice configuration (provider, voiceId, etc.)
            first_message: Initial greeting message
            system_prompt: System prompt for the assistant
            tools: List of tool definitions
            metadata: Additional metadata
            server_url: Webhook URL for function calls
            server_url_secret: Secret for webhook verification

        Returns:
            Created assistant data with ID
        """
        payload = {
            "name": name,
            "model": model,
            "voice": voice,
            "firstMessage": first_message,
        }

        if system_prompt:
            payload["model"]["messages"] = [
                {"role": "system", "content": system_prompt}
            ]

        if tools:
            payload["model"]["tools"] = tools

        if metadata:
            payload["metadata"] = metadata

        if server_url:
            payload["serverUrl"] = server_url

        if server_url_secret:
            payload["serverUrlSecret"] = server_url_secret

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/assistant",
                headers=self.headers,
                json=payload,
            )

            # Better error handling
            if response.status_code != 200:
                error_detail = response.text
                print(f"VAPI API Error: {response.status_code}")
                print(f"Response: {error_detail}")

            response.raise_for_status()
            return response.json()

    async def update_assistant(
        self,
        assistant_id: str,
        name: Optional[str] = None,
        model: Optional[Dict[str, Any]] = None,
        voice: Optional[Dict[str, Any]] = None,
        first_message: Optional[str] = None,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        server_url: Optional[str] = None,
        server_url_secret: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Update an existing VAPI assistant.

        Args:
            assistant_id: ID of the assistant to update
            name: Updated assistant name
            model: Updated model configuration
            voice: Updated voice configuration
            first_message: Updated greeting message
            system_prompt: Updated system prompt
            tools: Updated list of tools
            metadata: Updated metadata
            server_url: Updated webhook URL
            server_url_secret: Updated webhook secret
            **kwargs: Additional VAPI assistant configuration parameters
                     (silenceTimeoutSeconds, responseDelaySeconds, transcriber,
                      maxDurationSeconds, recordingEnabled, voicemailDetection, etc.)

        Returns:
            Updated assistant data
        """
        payload = {}

        if name:
            payload["name"] = name
        if model:
            payload["model"] = model
        if voice:
            payload["voice"] = voice
        if first_message:
            payload["firstMessage"] = first_message
        if system_prompt and model:
            payload["model"]["messages"] = [
                {"role": "system", "content": system_prompt}
            ]
        if tools and model:
            payload["model"]["tools"] = tools
        if metadata:
            payload["metadata"] = metadata
        if server_url:
            payload["serverUrl"] = server_url
        if server_url_secret:
            payload["serverUrlSecret"] = server_url_secret

        # Add any additional VAPI configuration parameters
        # (timing settings, transcriber, call settings, etc.)
        payload.update(kwargs)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.patch(
                f"{self.base_url}/assistant/{assistant_id}",
                headers=self.headers,
                json=payload,
            )

            # Better error handling
            if response.status_code != 200:
                error_detail = response.text
                print(f"VAPI API Error: {response.status_code}")
                print(f"Response: {error_detail}")
                print(f"Payload sent: {payload}")

            response.raise_for_status()
            return response.json()

    async def get_assistant(self, assistant_id: str) -> Dict[str, Any]:
        """
        Get assistant details by ID.

        Args:
            assistant_id: ID of the assistant

        Returns:
            Assistant data
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/assistant/{assistant_id}",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def list_assistants(self) -> List[Dict[str, Any]]:
        """
        List all assistants.

        Returns:
            List of assistant data
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/assistant",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def delete_assistant(self, assistant_id: str) -> Dict[str, Any]:
        """
        Delete an assistant.

        Args:
            assistant_id: ID of the assistant to delete

        Returns:
            Deletion confirmation
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{self.base_url}/assistant/{assistant_id}",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def create_phone_number(
        self,
        assistant_id: str,
        phone_number: Optional[str] = None,
        provider: str = "twilio",
        twilio_account_sid: Optional[str] = None,
        twilio_auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Link a phone number to an assistant.

        Args:
            assistant_id: ID of the assistant
            phone_number: Existing phone number to link (optional)
            provider: Phone provider (default: twilio)
            twilio_account_sid: Twilio account SID
            twilio_auth_token: Twilio auth token

        Returns:
            Phone number configuration
        """
        payload = {
            "assistantId": assistant_id,
            "provider": provider,
        }

        if phone_number:
            payload["number"] = phone_number

        if twilio_account_sid:
            payload["twilioAccountSid"] = twilio_account_sid

        if twilio_auth_token:
            payload["twilioAuthToken"] = twilio_auth_token

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/phone-number",
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def update_phone_number(
        self,
        phone_number_id: str,
        assistant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update phone number configuration.

        Args:
            phone_number_id: ID of the phone number
            assistant_id: Updated assistant ID to link

        Returns:
            Updated phone number configuration
        """
        payload = {}
        if assistant_id:
            payload["assistantId"] = assistant_id

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.patch(
                f"{self.base_url}/phone-number/{phone_number_id}",
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    def build_tool_definition(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        server_url: str,
    ) -> Dict[str, Any]:
        """
        Build a tool definition for VAPI.

        Args:
            name: Tool name
            description: Tool description
            parameters: JSON schema for parameters
            server_url: Webhook URL to call for this tool

        Returns:
            Tool definition dict
        """
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            },
            "server": {
                "url": server_url,
            },
        }

    def build_model_config(
        self,
        provider: str = "openai",
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 250,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Build model configuration.

        Args:
            provider: Model provider (openai, anthropic, etc.)
            model: Model name
            temperature: Temperature for generation
            max_tokens: Max tokens per response
            system_prompt: System prompt
            tools: List of tool definitions

        Returns:
            Model configuration dict
        """
        config = {
            "provider": provider,
            "model": model,
            "temperature": temperature,
            "maxTokens": max_tokens,
        }

        if system_prompt:
            config["messages"] = [{"role": "system", "content": system_prompt}]

        if tools:
            config["tools"] = tools

        return config

    def build_voice_config(
        self,
        provider: str = "11labs",
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
    ) -> Dict[str, Any]:
        """
        Build voice configuration.

        Args:
            provider: Voice provider (11labs, playht, azure, etc.)
            voice_id: Voice ID from provider
            stability: Voice stability (0-1)
            similarity_boost: Similarity boost (0-1)

        Returns:
            Voice configuration dict
        """
        return {
            "provider": provider,
            "voiceId": voice_id,
            "stability": stability,
            "similarityBoost": similarity_boost,
        }


# Singleton instance
vapi_client = VAPIClient()
