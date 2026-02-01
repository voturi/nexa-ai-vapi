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
    
    # Create phone number WITHOUT assistantId
    payload = {
        "provider": "twilio",
        "number": "+61468088108",
        "twilioAccountSid": settings.TWILIO_ACCOUNT_SID,
        "twilioAuthToken": settings.TWILIO_AUTH_TOKEN,
        "name": "Multi-tenant Receptionist",
        "server": {
            "url": f"{settings.BACKEND_URL}",
            "timeoutSeconds": 20
        }
        # NO assistantId - this triggers assistant-request!
    }
    
    print("📞 Creating phone number WITHOUT pre-assigned assistant...")
    print(f"   Number: +61468088108")
    print(f"   Server URL: {settings.BACKEND_URL}")
    print(f"   This will trigger 'assistant-request' webhook on incoming calls\n")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.vapi.ai/phone-number",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 201 or response.status_code == 200:
                result = response.json()
                print("✅ Phone number created successfully!")
                print(f"   Phone ID: {result['id']}")
                print(f"   Number: {result['number']}")
                print(f"   Server URL: {result.get('server', {}).get('url', 'Not set')}")
                print(f"   Assistant ID: {result.get('assistantId', '❌ None (will trigger assistant-request)')}")
                print(f"\n✅ Configuration correct for multi-tenant pattern!")
            else:
                print(f"❌ Failed: {response.status_code}")
                print(response.text)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(main())
