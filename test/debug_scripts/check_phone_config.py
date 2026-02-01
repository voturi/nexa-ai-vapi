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
    
    # Get phone number config
    phone_id = "abe13b19-cbed-404a-915b-a22ba818a3d3"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.vapi.ai/phone-number/{phone_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            phone_data = response.json()
            print("📞 Phone Number Configuration:")
            print(f"   Number: {phone_data.get('number')}")
            print(f"   Assistant ID: {phone_data.get('assistantId')}")
            
            if 'server' in phone_data:
                print(f"   Server URL: {phone_data['server'].get('url')}")
                print(f"   Server Timeout: {phone_data['server'].get('timeoutSeconds')}s")
            else:
                print("   Server: Not set at phone level")
            
            print("\n🔧 Expected Server URL:")
            print(f"   {settings.BACKEND_URL}")
            
            # Check if we need to update
            current_url = phone_data.get('server', {}).get('url', '')
            if current_url != settings.BACKEND_URL:
                print(f"\n❌ MISMATCH DETECTED!")
                print(f"   Current: {current_url}")
                print(f"   Expected: {settings.BACKEND_URL}")
                print(f"\n   This is why function calls are failing!")
                
                # Update it
                print(f"\n🔄 Updating phone number server URL...")
                update_response = await client.patch(
                    f"https://api.vapi.ai/phone-number/{phone_id}",
                    headers=headers,
                    json={
                        "server": {
                            "url": settings.BACKEND_URL,
                            "timeoutSeconds": 20
                        }
                    }
                )
                
                if update_response.status_code == 200:
                    print("✅ Phone number server URL updated successfully!")
                else:
                    print(f"❌ Update failed: {update_response.status_code}")
                    print(update_response.text)
            else:
                print("\n✅ Server URL is correct!")

asyncio.run(main())
