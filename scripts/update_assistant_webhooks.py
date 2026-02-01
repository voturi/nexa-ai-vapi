#!/usr/bin/env python3
"""
Update assistant webhook URLs to use ngrok.

Usage:
    python scripts/update_assistant_webhooks.py <assistant_id> <ngrok_url>
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.integrations.vapi_client import VAPIClient


async def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/update_assistant_webhooks.py <assistant_id> <ngrok_url>")
        print("\nExample:")
        print("  python scripts/update_assistant_webhooks.py 34d15667-5398-41c6-9736-07423df0aff5 https://logorrheic-nonbeneficent-sonny.ngrok-free.dev")
        sys.exit(1)

    assistant_id = sys.argv[1]
    ngrok_url = sys.argv[2].rstrip('/')

    print(f"\n🔄 Updating assistant webhooks...")
    print(f"   Assistant ID: {assistant_id}")
    print(f"   Ngrok URL: {ngrok_url}")

    client = VAPIClient()

    # Update assistant with correct webhook URL
    result = await client.update_assistant(
        assistant_id=assistant_id,
        server_url=f"{ngrok_url}/webhooks/vapi/call-started"
    )

    print(f"\n✅ Assistant updated successfully!")
    print(f"   Webhook URL: {ngrok_url}/webhooks/vapi/call-started")
    print(f"   Function URL: {ngrok_url}/webhooks/vapi/function-call")


if __name__ == "__main__":
    asyncio.run(main())
