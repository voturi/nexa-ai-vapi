"""Main FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import (
    connect_to_supabase,
    connect_to_redis,
    close_redis_connection,
)
from app.api.v1.api import api_router
from app.webhooks.vapi import router as vapi_webhook_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await connect_to_supabase()
    await connect_to_redis()
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
