#!/usr/bin/env python3
"""Verify assistant tools configuration."""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.integrations.vapi_client import VAPIClient


async def main():
    assistant_id = "34d15667-5398-41c6-9736-07423df0aff5"

    print("\n🔍 Verifying Tools Configuration\n")

    client = VAPIClient()
    assistant = await client.get_assistant(assistant_id)

    tools = assistant.get("model", {}).get("tools", [])

    print(f"✅ Found {len(tools)} tools\n")

    for i, tool in enumerate(tools, 1):
        func = tool.get("function", {})
        server = tool.get("server", {})

        print(f"{i}. {func.get('name')}")
        print(f"   Server URL: {server.get('url')}")
        print(f"   Description: {func.get('description')}")
        print(f"   Parameters: {list(func.get('parameters', {}).get('properties', {}).keys())}")
        print()

    # Check if server URLs are correct
    server_url = assistant.get("serverUrl")
    print(f"Assistant serverUrl: {server_url}")
    print(f"Expected: https://logorrheic-nonbeneficent-sonny.ngrok-free.dev/webhooks/vapi/call-started")

    if server_url == "https://logorrheic-nonbeneficent-sonny.ngrok-free.dev/webhooks/vapi/call-started":
        print("✅ Server URL is correct")
    else:
        print("⚠️  Server URL mismatch")


if __name__ == "__main__":
    asyncio.run(main())
