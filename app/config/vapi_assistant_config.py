"""
VAPI Assistant Configuration Settings

This module contains all available VAPI assistant configuration options.
Reference: https://docs.vapi.ai/api-reference/assistants/create-assistant
"""

from typing import Dict, Any, Optional


class VAPIAssistantConfig:
    """Complete VAPI Assistant configuration with all available settings."""

    @staticmethod
    def get_voice_interaction_settings(
        profile: str = "balanced"
    ) -> Dict[str, Any]:
        """
        Get voice interaction settings for different conversation styles.

        Note: silenceTimeoutSeconds has a minimum of 10s in VAPI API and is used
        for ending calls on extended silence, not for endpointing during conversation.
        Use responseDelaySeconds and transcriber settings to control interruptions.

        Profiles:
        - balanced: Good for most conversations (default)
        - patient: Wait longer for user to finish speaking (less interruptions)
        - responsive: Faster responses (more interruptions)
        - very_patient: Maximum wait time (for elderly, slow speakers)
        """
        profiles = {
            "responsive": {
                "responseDelaySeconds": 0.2,
                "transcriber": {
                    "provider": "deepgram",
                    "model": "nova-2",
                    "language": "en-AU",
                },
            },
            "balanced": {
                "responseDelaySeconds": 0.4,   # Slight delay before responding
                "transcriber": {
                    "provider": "deepgram",
                    "model": "nova-2",
                    "language": "en-AU",
                },
            },
            "patient": {
                "responseDelaySeconds": 0.6,   # Noticeable delay before responding
                "transcriber": {
                    "provider": "deepgram",
                    "model": "nova-2",
                    "language": "en-AU",
                },
            },
            "very_patient": {
                "responseDelaySeconds": 0.8,   # Long delay
                "transcriber": {
                    "provider": "deepgram",
                    "model": "nova-2",
                    "language": "en-AU",
                },
            },
        }

        return profiles.get(profile, profiles["balanced"])

    @staticmethod
    def get_voice_settings(
        provider: str = "11labs",
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        speed: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Voice synthesis settings.

        Args:
            provider: Voice provider (11labs, playht, azure, google, etc.)
            voice_id: Voice ID from the provider
            stability: Voice stability 0-1 (higher = more consistent)
            similarity_boost: Similarity to original voice 0-1
            speed: Speech speed multiplier (0.5-2.0, 1.0 = normal)
        """
        config = {
            "provider": provider,
            "voiceId": voice_id,
            "stability": stability,
            "similarityBoost": similarity_boost,
        }

        # Add speed if not default
        if speed != 1.0:
            config["speed"] = speed

        return config

    @staticmethod
    def get_model_settings(
        provider: str = "openai",
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 250,
        enable_emotions: bool = False,
    ) -> Dict[str, Any]:
        """
        LLM model settings.

        Args:
            provider: Model provider (openai, anthropic, groq, etc.)
            model: Model name
            temperature: Creativity 0-2 (higher = more creative/random)
            max_tokens: Max tokens per response (keep low for voice!)
            enable_emotions: Enable emotion detection
        """
        config = {
            "provider": provider,
            "model": model,
            "temperature": temperature,
            "maxTokens": max_tokens,
        }

        if enable_emotions:
            config["emotionRecognitionEnabled"] = True

        return config

    @staticmethod
    def get_call_settings(
        max_duration_seconds: int = 1800,        # 30 minutes max
        background_sound: str = "off",            # "off", "office", "cafe"
        recording_enabled: bool = True,
        hipaa_enabled: bool = False,
    ) -> Dict[str, Any]:
        """
        Overall call behavior settings.

        Note: silenceTimeoutSeconds should be set in voice interaction settings,
        not here, to avoid conflicts with endpointing configuration.

        Args:
            max_duration_seconds: Maximum call length
            background_sound: Background ambiance ("off", "office", "cafe")
            recording_enabled: Record calls
            hipaa_enabled: HIPAA compliant mode
        """
        config = {
            "maxDurationSeconds": max_duration_seconds,
            "recordingEnabled": recording_enabled,
        }

        if background_sound != "off":
            config["backgroundSound"] = background_sound

        if hipaa_enabled:
            config["hipaaEnabled"] = True

        return config

    @staticmethod
    def get_voicemail_settings(
        detection_enabled: bool = False,
        message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Voicemail detection settings.

        Args:
            detection_enabled: Detect voicemail and leave message
            message: Custom voicemail message (if None, uses firstMessage)
        """
        config = {}

        # According to VAPI API, voicemailDetection should be enabled via
        # the voicemailDetection object configuration
        # For now, skip voicemail detection to avoid API issues
        # if detection_enabled:
        #     config["voicemailDetection"] = {"enabled": True}
        #     if message:
        #         config["voicemailMessage"] = message

        return config

    @staticmethod
    def get_complete_config(
        interaction_profile: str = "patient",
        max_call_duration: int = 1800,
        recording_enabled: bool = True,
    ) -> Dict[str, Any]:
        """
        Get a complete configuration with all recommended settings.

        Args:
            interaction_profile: Voice interaction style (responsive, balanced, patient, very_patient)
            max_call_duration: Maximum call length in seconds
            recording_enabled: Whether to record calls
        """
        # Merge all settings
        config = {}

        # Voice interaction settings (silenceTimeout, responseDelay, transcriber)
        # These control when the AI detects user is done speaking
        config.update(
            VAPIAssistantConfig.get_voice_interaction_settings(interaction_profile)
        )

        # Call-level settings (max duration, recording)
        # Note: silenceTimeout is already set above for voice interaction
        config.update(
            VAPIAssistantConfig.get_call_settings(
                max_duration_seconds=max_call_duration,
                recording_enabled=recording_enabled,
            )
        )

        # Voicemail settings (disabled for now due to API format issues)
        config.update(
            VAPIAssistantConfig.get_voicemail_settings(
                detection_enabled=False,
            )
        )

        return config


# Preset configurations for common use cases
VAPI_PRESETS = {
    "customer_service": {
        "interaction_profile": "patient",
        "description": "Patient interaction, good for customer service calls",
    },
    "sales": {
        "interaction_profile": "balanced",
        "description": "Balanced interaction for sales conversations",
    },
    "support": {
        "interaction_profile": "patient",
        "description": "Patient for technical support calls",
    },
    "emergency": {
        "interaction_profile": "responsive",
        "description": "Quick responses for emergency/urgent situations",
    },
    "elderly_friendly": {
        "interaction_profile": "very_patient",
        "description": "Maximum patience for elderly callers or slow speakers",
    },
}
