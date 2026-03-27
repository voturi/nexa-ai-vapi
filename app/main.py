"""Main FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import (
    connect_to_supabase,
    connect_to_redis,
    close_redis_connection,
    AsyncSessionLocal,
)
from app.api.v1.api import api_router
from app.webhooks.vapi import router as vapi_webhook_router
from app.services.assistant_cache import assistant_cache


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await connect_to_supabase()
    await connect_to_redis()

    # Warm up assistant cache
    print("🔥 Warming up assistant cache...")
    async with AsyncSessionLocal() as db:
        await assistant_cache.warm_cache(db)

        # Setup phone number mappings (hardcoded for now)
        # In production, you'd query a phone_numbers table
        assistant_cache.set_phone_mapping(
            "0136cdb1-1eae-41e9-a695-dea2c28ebe60",  # Phone number ID
            "2ad294ed-0d2c-4259-a7fd-300d7989efc8"   # Mike's Plumbing tenant ID
        )

    print("✅ Assistant cache warmed and ready!")

    yield
    # Shutdown
    await close_redis_connection()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    lifespan=lifespan,
)

# CORS middleware
cors_origins = [settings.FRONTEND_URL]
if settings.ENVIRONMENT == "development":
    cors_origins.append("http://localhost:3001")
    cors_origins.append("http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origin_regex=r"https://nexa-ai-vapi-frontend.*\.vercel\.app",
)

# API routes
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# Webhook routes
app.include_router(vapi_webhook_router, prefix="/webhooks/vapi", tags=["webhooks"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.VERSION}


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    return {"status": "ready"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
    )
