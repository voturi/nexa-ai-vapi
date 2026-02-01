#!/usr/bin/env python3
"""
Update VAPI assistant voice interaction settings.

Usage:
    python scripts/update_assistant_settings.py <assistant_id> [profile]

Profiles: responsive, balanced, patient, very_patient
Default: patient (recommended for customer service)

Example:
    python scripts/update_assistant_settings.py 34d15667-5398-41c6-9736-07423df0aff5 patient
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.integrations.vapi_client import VAPIClient
from app.config.vapi_assistant_config import VAPIAssistantConfig, VAPI_PRESETS


async def main():
    if len(sys.argv) < 2:
        assistant_id = "34d15667-5398-41c6-9736-07423df0aff5"
        profile = "patient"
    elif len(sys.argv) < 3:
        assistant_id = sys.argv[1]
        profile = "patient"
    else:
        assistant_id = sys.argv[1]
        profile = sys.argv[2]

    # Validate profile
    valid_profiles = list(VAPI_PRESETS.keys())
    if profile not in ["responsive", "balanced", "patient", "very_patient"]:
        print(f"❌ Invalid profile: {profile}")
        print(f"   Valid profiles: responsive, balanced, patient, very_patient")
        print(f"\nPreset Descriptions:")
        for preset_name, preset_info in VAPI_PRESETS.items():
            print(f"   - {preset_name}: {preset_info['description']}")
        sys.exit(1)

    print(f"\n🔧 Updating Assistant Voice Interaction Settings")
    print(f"=" * 70)
    print(f"   Assistant ID: {assistant_id}")
    print(f"   Profile: {profile}")
    print(f"=" * 70 + "\n")

    # Get the complete configuration
    config = VAPIAssistantConfig.get_complete_config(
        interaction_profile=profile,
        max_call_duration=1800,  # 30 minutes
        recording_enabled=True,
    )

    print(f"📋 Configuration to Apply:")
    print(f"   Silence Timeout: {config.get('silenceTimeoutSeconds')}s")
    print(f"   Response Delay: {config.get('responseDelaySeconds')}s")
    print(f"   Transcriber: {config.get('transcriber', {}).get('provider')} ({config.get('transcriber', {}).get('model')})")
    print(f"   Language: {config.get('transcriber', {}).get('language')}")
    print(f"   Max Call Duration: {config.get('maxDurationSeconds')}s ({config.get('maxDurationSeconds')//60} minutes)")
    print(f"   Recording: {config.get('recordingEnabled')}")
    print(f"   Voicemail Detection: {config.get('voicemailDetection', {}).get('enabled', False)}")
    print()

    # Update the assistant
    client = VAPIClient()

    print("⏳ Updating assistant...")

    try:
        result = await client.update_assistant(
            assistant_id=assistant_id,
            **config
        )

        print("✅ Assistant updated successfully!")
        print(f"\n📝 New Settings Applied:")
        print(f"   - AI will wait {config.get('silenceTimeoutSeconds')}s of silence before responding")
        print(f"   - {config.get('responseDelaySeconds')}s delay before AI starts talking")
        print(f"   - Using Deepgram Nova-2 transcriber for Australian English")
        print(f"   - Less likely to interrupt mid-sentence")
        print()
        print(f"🎯 Result: The AI should be much less interruptive now!")
        print(f"   Try making a test call and pause naturally - it won't cut you off.")

    except Exception as e:
        print(f"❌ Failed to update assistant: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
