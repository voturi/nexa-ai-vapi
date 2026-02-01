#!/usr/bin/env python3
import sys
import asyncio
import httpx
sys.path.insert(0, '/Users/praveen.voturi/Documents/ai_receptionist_vapi/backend')

from app.core.config import settings

async def main():
    headers = {
        "Authorization": f"Bearer {settings.VAPI_API_KEY}",
        "Content-Type": "application/json"
    }

    phone_id = "0136cdb1-1eae-41e9-a695-dea2c28ebe60"

    # Update server URL to include the full webhook path
    payload = {
        "server": {
            "url": f"{settings.BACKEND_URL}/webhooks/vapi/call-started",
            "timeoutSeconds": 20
        }
    }

    print("🔧 Updating phone number server URL...")
    print(f"   Phone: +61255644466")
    print(f"   New Server URL: {settings.BACKEND_URL}/webhooks/vapi/call-started")
    print(f"   This is the correct path for assistant-request webhook\n")

    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"https://api.vapi.ai/phone-number/{phone_id}",
            headers=headers,
            json=payload
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ Phone number updated successfully!")
            print(f"   Number: {result['number']}")
            print(f"   Server URL: {result.get('server', {}).get('url', 'Not set')}")
            print(f"\nNow VAPI will POST assistant-request to:")
            print(f"   {result.get('server', {}).get('url')}")
        else:
            print(f"❌ Update failed: {response.status_code}")
            print(response.text)

asyncio.run(main())
