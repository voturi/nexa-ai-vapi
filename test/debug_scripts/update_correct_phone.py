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
    
    # First, list phone numbers to find the ID for +61255644466
    async with httpx.AsyncClient() as client:
        list_response = await client.get(
            "https://api.vapi.ai/phone-number",
            headers=headers
        )
        
        if list_response.status_code == 200:
            phones = list_response.json()
            target_phone = None
            
            for phone in phones:
                if phone.get('number') == '+61255644466':
                    target_phone = phone
                    break
            
            if not target_phone:
                print("❌ Phone number +61255644466 not found!")
                return
            
            phone_id = target_phone['id']
            print(f"📞 Found phone number: {target_phone['number']}")
            print(f"   Phone ID: {phone_id}")
            print(f"   Current Assistant: {target_phone.get('assistantId', 'None')}\n")
            
            # Update to remove assistant and set server URL for assistant-request
            payload = {
                "assistantId": None,  # Remove assistant assignment
                "name": "Multi-tenant Receptionist",
                "server": {
                    "url": f"{settings.BACKEND_URL}",
                    "timeoutSeconds": 20
                }
            }
            
            print("🔧 Updating phone number configuration...")
            print(f"   Removing assistant assignment...")
            print(f"   Server URL: {settings.BACKEND_URL}")
            print(f"   This will trigger 'assistant-request' webhook\n")
            
            update_response = await client.patch(
                f"https://api.vapi.ai/phone-number/{phone_id}",
                headers=headers,
                json=payload
            )
            
            if update_response.status_code == 200:
                result = update_response.json()
                print("✅ Phone number updated successfully!")
                print(f"   Number: {result['number']}")
                print(f"   Server URL: {result.get('server', {}).get('url', 'Not set')}")
                
                assistant_id = result.get('assistantId')
                if assistant_id:
                    print(f"   ⚠️  Assistant ID: {assistant_id} (still assigned - may need manual removal)")
                else:
                    print(f"   ✅ Assistant ID: None")
                    print(f"\n✅ Configuration correct for multi-tenant pattern!")
                    print(f"\nNow when a call comes in:")
                    print(f"  1. VAPI sends 'assistant-request' to {settings.BACKEND_URL}")
                    print(f"  2. Backend identifies tenant from phone/metadata")
                    print(f"  3. Backend returns the correct assistant configuration")
                    print(f"  4. Tools work because they're defined in the returned assistant")
            else:
                print(f"❌ Update failed: {update_response.status_code}")
                print(update_response.text)
        else:
            print(f"❌ Failed to list phone numbers: {list_response.status_code}")

asyncio.run(main())
