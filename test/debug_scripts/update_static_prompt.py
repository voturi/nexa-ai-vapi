#!/usr/bin/env python3
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, '/Users/praveen.voturi/Documents/ai_receptionist_vapi/backend')

from app.integrations.vapi_client import VAPIClient

async def main():
    assistant_id = "34d15667-5398-41c6-9736-07423df0aff5"
    
    # Get current config
    client = VAPIClient()
    assistant = await client.get_assistant(assistant_id)
    
    # Get existing system prompt
    current_messages = assistant.get("model", {}).get("messages", [])
    if current_messages:
        current_prompt = current_messages[0].get("content", "")
        
        # Add date context to the beginning
        date_context = """
IMPORTANT CONTEXT:
- Today's date is 2026-02-01 (February 1st, 2026)
- Current year: 2026
- When checking availability or booking appointments, ALWAYS use dates in 2026 format (YYYY-MM-DD)
- When the user asks for "tomorrow", that means 2026-02-02
- When the user asks for "next week", that means dates in February 2026

"""
        
        new_prompt = date_context + current_prompt
        
        # Update assistant
        result = await client.update_assistant(
            assistant_id=assistant_id,
            model={
                "provider": "openai",
                "model": "gpt-4o-mini",
                "temperature": 0.7,
                "maxTokens": 250,
                "messages": [
                    {
                        "role": "system",
                        "content": new_prompt
                    }
                ],
                "tools": assistant["model"]["tools"]  # Keep existing tools
            }
        )
        
        print("✅ Updated assistant with date context in static prompt")
        print(f"New prompt length: {len(new_prompt)} characters")
    else:
        print("❌ No existing messages found")

if __name__ == "__main__":
    asyncio.run(main())
