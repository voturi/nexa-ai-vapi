#!/usr/bin/env python3
"""
Check VAPI assistant details.

Usage:
    python scripts/check_assistant.py <assistant_id>
"""
import sys
import asyncio
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.integrations.vapi_client import VAPIClient


async def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_assistant.py <assistant_id>")
        sys.exit(1)

    assistant_id = sys.argv[1]

    print(f"\n🔍 Fetching assistant details...")
    print(f"   Assistant ID: {assistant_id}\n")

    client = VAPIClient()
    assistant = await client.get_assistant(assistant_id)

    print("=" * 80)
    print("ASSISTANT DETAILS")
    print("=" * 80)
    print(json.dumps(assistant, indent=2))

    # Extract and display tools specifically
    if "model" in assistant and "tools" in assistant["model"]:
        tools = assistant["model"]["tools"]
        print("\n" + "=" * 80)
        print(f"TOOLS REGISTERED: {len(tools)}")
        print("=" * 80)
        for i, tool in enumerate(tools, 1):
            print(f"\n{i}. {tool['function']['name']}")
            print(f"   Description: {tool['function']['description']}")
            print(f"   Server URL: {tool.get('server', {}).get('url', 'N/A')}")
    else:
        print("\n⚠️  No tools found in assistant configuration")


if __name__ == "__main__":
    asyncio.run(main())
