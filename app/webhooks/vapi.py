"""VAPI webhook handlers."""
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_webhook_signature
from app.services.vapi_service import VAPIService
from app.services.call_service import CallService

router = APIRouter()


@router.post("/call-started")
async def handle_call_started(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle call started webhook from VAPI.

    Triggered when a call begins. This is where we inject dynamic context
    and tenant-specific prompts.
    """
    body = await request.body()
    data = await request.json()

    # Extract tenant_id from metadata
    tenant_id = data.get("call", {}).get("metadata", {}).get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Missing tenant_id in metadata")

    # Verify webhook signature (optional but recommended)
    # signature = request.headers.get("X-VAPI-Signature")
    # if signature and not verify_webhook_signature(signature, body, tenant.webhook_secret):
    #     raise HTTPException(status_code=401, detail="Invalid signature")

    # Process call started event
    vapi_service = VAPIService(db)
    response_data = await vapi_service.handle_call_started(data)

    return response_data


@router.post("/function-call")
async def handle_function_call(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle function call webhook from VAPI.

    Triggered when AI calls a tool/function. Execute integration actions
    with tenant-specific credentials.
    """
    body = await request.body()
    data = await request.json()

    # Extract tenant_id from metadata
    tenant_id = data.get("call", {}).get("metadata", {}).get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Missing tenant_id in metadata")

    # Process function call
    vapi_service = VAPIService(db)
    result = await vapi_service.handle_function_call(data)

    return {"result": result}


@router.post("/call-ended")
async def handle_call_ended(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle call ended webhook from VAPI.

    Triggered when call completes. Process transcript, save recording,
    update analytics.
    """
    body = await request.body()
    data = await request.json()

    # Extract tenant_id from metadata
    tenant_id = data.get("call", {}).get("metadata", {}).get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Missing tenant_id in metadata")

    # Process call ended event
    call_service = CallService(db)
    await call_service.handle_call_ended(data)

    return {"status": "processed"}


@router.post("/call-status")
async def handle_call_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle call status webhook from VAPI.

    Triggered when call status changes (ringing, answered, etc.)
    """
    body = await request.body()
    data = await request.json()

    # Extract tenant_id from metadata
    tenant_id = data.get("call", {}).get("metadata", {}).get("tenant_id")
    if not tenant_id:
        return {"status": "ignored"}  # Optional tracking

    # Process call status update
    call_service = CallService(db)
    await call_service.handle_call_status(data)

    return {"status": "processed"}
