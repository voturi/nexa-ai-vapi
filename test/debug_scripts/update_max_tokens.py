#!/usr/bin/env python3
import sys
import asyncio
sys.path.insert(0, '/Users/praveen.voturi/Documents/ai_receptionist_vapi/backend')

from app.integrations.vapi_client import VAPIClient

async def main():
    client = VAPIClient()
    assistant_id = "34d15667-5398-41c6-9736-07423df0aff5"
    
    # Get current assistant
    assistant = await client.get_assistant(assistant_id)
    
    # Update with higher maxTokens
    await client.update_assistant(
        assistant_id=assistant_id,
        model={
            "provider": "openai",
            "model": "gpt-4o-mini",
            "temperature": 0.7,
            "maxTokens": 500,  # Increased from 250
            "messages": assistant["model"]["messages"],
            "tools": assistant["model"]["tools"]
        }
    )
    
    print("✅ Updated maxTokens to 500")

asyncio.run(main())
