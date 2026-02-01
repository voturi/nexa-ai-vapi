#!/usr/bin/env python3
import sys
import asyncio
sys.path.insert(0, '/Users/praveen.voturi/Documents/ai_receptionist_vapi/backend')

from app.integrations.vapi_client import VAPIClient
from app.core.config import settings

async def main():
    client = VAPIClient()
    
    # Create phone number WITHOUT assistant assignment
    # The server URL will handle assistant-request
    phone_config = {
        "provider": "twilio",
        "number": "+61468088108",  # Your existing Twilio number
        "twilioAccountSid": settings.TWILIO_ACCOUNT_SID,
        "twilioAuthToken": settings.TWILIO_AUTH_TOKEN,
        "name": "Multi-tenant Receptionist",
        "server": {
            "url": f"{settings.BACKEND_URL}",  # Base URL, not /call-started
            "timeoutSeconds": 20
        }
        # NOTE: NO assistantId here! This triggers assistant-request
    }
    
    print("📞 Creating phone number WITHOUT pre-assigned assistant...")
    print(f"   Number: +61468088108")
    print(f"   Server URL: {settings.BACKEND_URL}")
    print(f"   This will trigger 'assistant-request' webhook\n")
    
    try:
        result = await client.create_phone_number(
            phone_number="+61468088108",
            provider="twilio",
            twilio_account_sid=settings.TWILIO_ACCOUNT_SID,
            twilio_auth_token=settings.TWILIO_AUTH_TOKEN
        )
        
        # Now update it with the server URL
        import httpx
        headers = {
            "Authorization": f"Bearer {settings.VAPI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as http_client:
            update_response = await http_client.patch(
                f"https://api.vapi.ai/phone-number/{result['id']}",
                headers=headers,
                json={
                    "name": "Multi-tenant Receptionist",
                    "server": {
                        "url": f"{settings.BACKEND_URL}",
                        "timeoutSeconds": 20
                    }
                }
            )
            
            if update_response.status_code == 200:
                updated = update_response.json()
                print("✅ Phone number created successfully!")
                print(f"   Phone ID: {updated['id']}")
                print(f"   Number: {updated['number']}")
                print(f"   Server URL: {updated.get('server', {}).get('url', 'Not set')}")
                print(f"   Assistant ID: {updated.get('assistantId', 'None - will use assistant-request')}")
            else:
                print(f"❌ Update failed: {update_response.status_code}")
                print(update_response.text)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(main())
