"""Application configuration."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""

    # API
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "nexa_receptionist_systems"
    VERSION: str = "1.0.0"

    # Database (Supabase)
    DATABASE_URL: Optional[str] = None
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    SUPABASE_SERVICE_KEY: Optional[str] = None
    REDIS_URL: str = "redis://localhost:6379"

    # VAPI
    VAPI_API_KEY: Optional[str] = None
    VAPI_BASE_URL: str = "https://api.vapi.ai"

    # Twilio
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None

    # Security
    ENCRYPTION_KEY: str = "development-key-change-in-production"
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days

    # URLs
    BACKEND_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"

    # Environment
    ENVIRONMENT: str = "development"

    # Google OAuth
    GOOGLE_OAUTH_CLIENT_ID: Optional[str] = None
    GOOGLE_OAUTH_CLIENT_SECRET: Optional[str] = None
    GOOGLE_OAUTH_REDIRECT_URI: Optional[str] = None

    # HubSpot
    HUBSPOT_CLIENT_ID: Optional[str] = None
    HUBSPOT_CLIENT_SECRET: Optional[str] = None

    # Stripe
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None

    # Feature Flags
    ENABLE_RECORDING: bool = True
    ENABLE_ANALYTICS: bool = True
    MAX_CALL_DURATION_SECONDS: int = 600

    # Monitoring
    SENTRY_DSN: Optional[str] = None
    LOG_LEVEL: str = "INFO"

    # Skills
    SKILLS_BASE_PATH: str = "./skills"

    # Pydantic v2 configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Allow extra fields in .env file
    )


settings = Settings()
