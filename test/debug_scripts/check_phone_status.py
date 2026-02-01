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

    print("📞 Checking VAPI phone number configurations...\n")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.vapi.ai/phone-number",
            headers=headers
        )

        if response.status_code == 200:
            phones = response.json()

            if not phones:
                print("❌ No phone numbers found in VAPI account")
                return

            print(f"Found {len(phones)} phone number(s):\n")
            print("="*80)

            for idx, phone in enumerate(phones, 1):
                print(f"\n📱 Phone #{idx}")
                print(f"   Number: {phone.get('number', 'N/A')}")
                print(f"   Phone ID: {phone.get('id', 'N/A')}")
                print(f"   Name: {phone.get('name', 'N/A')}")

                assistant_id = phone.get('assistantId')
                if assistant_id:
                    print(f"   ❌ Assistant ID: {assistant_id} (PRE-ASSIGNED - NOT MULTI-TENANT)")
                else:
                    print(f"   ✅ Assistant ID: None (MULTI-TENANT MODE)")

                server_config = phone.get('server', {})
                server_url = server_config.get('url') if server_config else None

                if server_url:
                    print(f"   ✅ Server URL: {server_url}")
                    timeout = server_config.get('timeoutSeconds', 'N/A')
                    print(f"   Server Timeout: {timeout}s")
                else:
                    print(f"   ❌ Server URL: Not configured")

                # Check if configuration is correct for multi-tenant
                print(f"\n   Configuration Status:")
                if not assistant_id and server_url:
                    print(f"   ✅ CORRECT - Will trigger 'assistant-request' webhook")
                    print(f"   ✅ Backend will dynamically assign assistant per tenant")
                elif assistant_id and server_url:
                    print(f"   ⚠️  MIXED - Has both assistant and server URL")
                    print(f"   ⚠️  VAPI will use pre-assigned assistant, NOT assistant-request")
                elif assistant_id and not server_url:
                    print(f"   ❌ WRONG - Pre-assigned assistant without server URL")
                    print(f"   ❌ Cannot support multi-tenant pattern")
                else:
                    print(f"   ❌ WRONG - No assistant and no server URL")
                    print(f"   ❌ Phone number not properly configured")

                print("="*80)

            print(f"\n\n🎯 MULTI-TENANT REQUIREMENTS:")
            print(f"   1. Assistant ID must be NULL (no pre-assignment)")
            print(f"   2. Server URL must be set to: {settings.BACKEND_URL}")
            print(f"   3. On incoming call, VAPI sends 'assistant-request' to server URL")
            print(f"   4. Backend identifies tenant and returns assistant config\n")

        else:
            print(f"❌ Failed to list phone numbers: {response.status_code}")
            print(response.text)

asyncio.run(main())
