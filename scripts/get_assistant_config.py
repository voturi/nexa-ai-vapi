#!/usr/bin/env python3
"""
Get full assistant configuration to see all settings.

Usage:
    python scripts/get_assistant_config.py <assistant_id>
"""
import sys
import asyncio
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.integrations.vapi_client import VAPIClient


async def main():
    if len(sys.argv) < 2:
        assistant_id = "34d15667-5398-41c6-9736-07423df0aff5"
    else:
        assistant_id = sys.argv[1]

    print(f"\n🔍 Fetching full assistant configuration...")
    print(f"   Assistant ID: {assistant_id}\n")

    client = VAPIClient()
    assistant = await client.get_assistant(assistant_id)

    print("=" * 80)
    print("FULL ASSISTANT CONFIGURATION")
    print("=" * 80)
    print(json.dumps(assistant, indent=2))

    # Highlight specific settings
    print("\n" + "=" * 80)
    print("KEY VOICE INTERACTION SETTINGS")
    print("=" * 80)

    model = assistant.get("model", {})
    print(f"\n📊 Model Settings:")
    print(f"   Model: {model.get('model')}")
    print(f"   Temperature: {model.get('temperature')}")
    print(f"   Max Tokens: {model.get('maxTokens')}")

    voice = assistant.get("voice", {})
    print(f"\n🎤 Voice Settings:")
    print(f"   Provider: {voice.get('provider')}")
    print(f"   Voice ID: {voice.get('voiceId')}")
    print(f"   Stability: {voice.get('stability')}")
    print(f"   Similarity Boost: {voice.get('similarityBoost')}")

    # Check for transcriber settings
    transcriber = assistant.get("transcriber", {})
    if transcriber:
        print(f"\n🎧 Transcriber Settings:")
        print(f"   Provider: {transcriber.get('provider', 'Not set')}")
        print(f"   Model: {transcriber.get('model', 'Not set')}")
        print(f"   Language: {transcriber.get('language', 'Not set')}")
    else:
        print(f"\n🎧 Transcriber Settings: Using defaults")

    # Check for silence/endpointing settings
    print(f"\n⏱️  Timing Settings:")
    print(f"   Silence Timeout: {assistant.get('silenceTimeoutSeconds', 'Not set')}")
    print(f"   Max Duration: {assistant.get('maxDurationSeconds', 'Not set')}")
    print(f"   Response Delay: {assistant.get('responseDelaySeconds', 'Not set')}")
    print(f"   Background Sound: {assistant.get('backgroundSound', 'Not set')}")

    # Voice mail detection
    print(f"\n📞 Call Behavior:")
    print(f"   Voicemail Detection: {assistant.get('voicemailDetection', 'Not set')}")
    print(f"   End Call On Silence: {assistant.get('endCallOnSilence', 'Not set')}")
    print(f"   Record Calls: {assistant.get('recordingEnabled', 'Not set')}")


if __name__ == "__main__":
    asyncio.run(main())
