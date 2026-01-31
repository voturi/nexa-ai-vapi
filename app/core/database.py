"""Database configuration and session management."""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
import redis.asyncio as redis
from supabase import create_client, Client
from typing import AsyncGenerator, Optional

from app.core.config import settings

# PostgreSQL (via Supabase)
engine: Optional[AsyncSession] = None
AsyncSessionLocal: Optional[async_sessionmaker] = None

if settings.DATABASE_URL:
    # Convert postgresql:// to postgresql+asyncpg:// for async driver
    database_url = settings.DATABASE_URL
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(
        database_url,
        echo=settings.ENVIRONMENT == "development",
        future=True,
    )

    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    if not AsyncSessionLocal:
        raise RuntimeError(
            "Database not configured. Please set DATABASE_URL in .env file."
        )

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Supabase Client
supabase_client: Optional[Client] = None


def get_supabase() -> Optional[Client]:
    """Get Supabase client."""
    return supabase_client


async def connect_to_supabase():
    """Connect to Supabase."""
    global supabase_client

    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        print("⚠️  Supabase not configured - skipping connection")
        return

    try:
        supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )
        print("✅ Connected to Supabase")
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")


# Redis
redis_client: Optional[redis.Redis] = None


async def get_redis():
    """Get Redis client."""
    return redis_client


async def connect_to_redis():
    """Connect to Redis."""
    global redis_client

    try:
        redis_client = await redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
        # Test connection
        await redis_client.ping()
        print("✅ Connected to Redis")
    except Exception as e:
        print(f"⚠️  Redis connection failed: {e}")
        print("   Some features may not work without Redis")
        redis_client = None


async def close_redis_connection():
    """Close Redis connection."""
    if redis_client:
        await redis_client.close()
        print("✅ Redis connection closed")
