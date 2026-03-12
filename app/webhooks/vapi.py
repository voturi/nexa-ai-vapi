"""VAPI webhook handlers."""
import json
import structlog
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_webhook_signature
from app.services.vapi_service import VAPIService
from app.services.call_service import CallService
from app.services.assistant_cache import assistant_cache

router = APIRouter()
logger = structlog.get_logger()


async def extract_tenant_id(data: dict, db) -> str:
    """
    Extract tenant_id from VAPI webhook payload.

    VAPI can send tenant_id in different locations depending on webhook type.
    For assistant-request (no pre-assigned assistant), we identify tenant by phone number.
    """
    # Handle None or invalid data
    if not data or not isinstance(data, dict):
        logger.error("extract_tenant_id_invalid_data", data_type=type(data).__name__)
        return None

    # Try message.assistant.metadata.tenant_id (call-started with assistant info)
    if "message" in data:
        message = data["message"]

        # For assistant.started events, check message.newAssistant.metadata
        new_assistant = message.get("newAssistant")
        if new_assistant:
            metadata = new_assistant.get("metadata")
            if metadata:
                tenant_id = metadata.get("tenant_id")
                if tenant_id:
                    return tenant_id

        # For tool-calls, check message.assistant.metadata first
        assistant = message.get("assistant")
        if assistant:
            metadata = assistant.get("metadata")
            if metadata:
                tenant_id = metadata.get("tenant_id")
                if tenant_id:
                    return tenant_id

        # For tool-calls, also check message.call (nested structure)
        call = message.get("call")
        if call:
            # Check call.assistant.metadata
            call_assistant = call.get("assistant")
            if call_assistant:
                metadata = call_assistant.get("metadata")
                if metadata:
                    tenant_id = metadata.get("tenant_id")
                    if tenant_id:
                        return tenant_id
            # Check call.metadata directly
            metadata = call.get("metadata")
            if metadata:
                tenant_id = metadata.get("tenant_id")
                if tenant_id:
                    return tenant_id

        # Try message.metadata.tenant_id
        metadata = message.get("metadata")
        if metadata:
            tenant_id = metadata.get("tenant_id")
            if tenant_id:
                return tenant_id

    # Try call.metadata.tenant_id (root level function-call)
    call = data.get("call")
    if call:
        metadata = call.get("metadata")
        if metadata:
            tenant_id = metadata.get("tenant_id")
            if tenant_id:
                return tenant_id

    # Try assistant.metadata.tenant_id (root level)
    assistant = data.get("assistant")
    if assistant:
        metadata = assistant.get("metadata")
        if metadata:
            tenant_id = metadata.get("tenant_id")
            if tenant_id:
                return tenant_id

    # For assistant-request: identify tenant by phone number
    # This is the multi-tenant pattern where different tenants use different phone numbers
    phone_number_id = None

    # Check for phoneNumber in root level (some webhooks)
    phone_obj = data.get("phoneNumber")
    if phone_obj:
        phone_number_id = phone_obj.get("id")

    # Check for phoneNumber in message (assistant-request)
    if not phone_number_id:
        message = data.get("message")
        if message:
            phone_obj = message.get("phoneNumber")
            if phone_obj:
                phone_number_id = phone_obj.get("id")

            # Check for phoneNumberId in message.call
            if not phone_number_id:
                call = message.get("call")
                if call:
                    phone_number_id = call.get("phoneNumberId")

    # Check for phoneNumberId in call (root level)
    if not phone_number_id:
        call = data.get("call")
        if call:
            phone_number_id = call.get("phoneNumberId")

    if phone_number_id:
        # Use cached phone-to-tenant mapping (FAST!)
        tenant_id = assistant_cache.get_tenant_by_phone(phone_number_id)
        if tenant_id:
            logger.info("tenant_identified_by_phone_cache", phone_number_id=phone_number_id, tenant_id=tenant_id)
            return tenant_id
        else:
            logger.warning("phone_not_mapped", phone_number_id=phone_number_id)

    logger.warning("tenant_not_identified", data_keys=list(data.keys()))
    return None


@router.post("/debug")
async def debug_webhook(request: Request):
    """Debug endpoint to see what VAPI is sending."""
    body = await request.body()
    data = await request.json()

    logger.info(
        "webhook_debug",
        method=request.method,
        headers=dict(request.headers),
        body=json.dumps(data, indent=2)
    )

    print("\n" + "="*80)
    print("VAPI WEBHOOK DEBUG")
    print("="*80)
    print(f"Method: {request.method}")
    print(f"Headers: {dict(request.headers)}")
    print(f"Body: {json.dumps(data, indent=2)}")
    print("="*80 + "\n")

    return {"status": "ok", "received": data}


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
    try:
        body = await request.body()
        data = await request.json()

        # Validate data
        if not data or not isinstance(data, dict):
            logger.error("webhook_call_started_invalid_data", body=body.decode('utf-8')[:500])
            return {"error": "Invalid request data"}

        # Check message type - VAPI sends different types to this endpoint
        message_type = data.get("message", {}).get("type")

        # Extract tenant_id using helper function
        tenant_id = await extract_tenant_id(data, db)

        # Log the incoming webhook
        logger.info(
            "webhook_call_started_received",
            tenant_id=tenant_id,
            message_type=message_type,
            data_keys=list(data.keys())
        )

        # Handle end-of-call-report (VAPI sometimes sends this here)
        if message_type == "end-of-call-report":
            logger.info(
                "end_of_call_report_received",
                tenant_id=tenant_id,
                summary=data.get("message", {}).get("analysis", {}).get("summary", "")[:100]
            )
            # Just return success - we handle this in call-ended webhook
            return {"status": "acknowledged"}

        # Handle assistant.started - just acknowledge it, don't override
        if message_type == "assistant.started":
            logger.info(
                "webhook_assistant_started",
                message_type=message_type,
                tenant_id=tenant_id
            )
            # Just acknowledge - the assistant is already configured
            return {"status": "acknowledged"}

        # Handle other non-call-start message types
        # VAPI sends "assistant-request" when we need to provide dynamic config
        if message_type and message_type != "assistant-request":
            logger.info(
                "webhook_call_started_other_type",
                message_type=message_type,
                tenant_id=tenant_id
            )
            return {"status": "acknowledged"}

        if not tenant_id:
            logger.error(
                "webhook_call_started_missing_tenant_id",
                payload=json.dumps(data, indent=2)
            )
            # Return empty response to not block the call
            # The assistant will use its default configuration
            return {}

        # Try to get cached assistant config first (FAST PATH)
        response_data = assistant_cache.get(tenant_id)

        if response_data:
            logger.info(
                "webhook_call_started_cache_hit",
                tenant_id=tenant_id,
                message_type=message_type
            )
        else:
            # Cache miss - build from scratch (SLOW PATH - only on first call or cache invalidation)
            logger.warning(
                "webhook_call_started_cache_miss",
                tenant_id=tenant_id,
                message_type=message_type
            )
            vapi_service = VAPIService(db)
            response_data = await vapi_service.handle_call_started(data, tenant_id=tenant_id)

            # Cache it for next time
            assistant_cache.set(tenant_id, response_data)

        logger.info(
            "webhook_call_started_success",
            tenant_id=tenant_id,
            message_type=message_type,
            has_assistant_override=("assistant" in response_data),
            response_keys=list(response_data.keys())
        )

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "webhook_call_started_error",
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


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
    try:
        body = await request.body()
        data = await request.json()

        # Check message type - VAPI sends multiple types to this endpoint
        message = data.get("message", {})
        message_type = message.get("type")

        # Extract tenant_id using helper function
        tenant_id = await extract_tenant_id(data, db)

        # Log the incoming webhook
        logger.info(
            "webhook_function_call_received",
            tenant_id=tenant_id,
            message_type=message_type,
            data_keys=list(data.keys()),
            message_keys=list(message.keys()) if message else []
        )

        # Handle end-of-call-report — VAPI sends this to serverUrl, not to /call-ended
        if message_type == "end-of-call-report":
            try:
                call_service = CallService(db)
                call = await call_service.handle_call_ended(data)
                logger.info(
                    "end_of_call_report_saved",
                    call_id=str(call.id) if call else None,
                    tenant_id=tenant_id,
                )
            except Exception as e:
                logger.error("end_of_call_report_save_failed", error=str(e))
            return {"status": "acknowledged"}

        # VAPI sends MANY webhook types to serverUrl
        # We ONLY process "tool-calls" type messages
        if message_type != "tool-calls":
            logger.debug(
                "webhook_serverurl_ignored",
                message_type=message_type,
                reason="Not a tool-calls message"
            )
            return {"status": "acknowledged"}

        if not tenant_id:
            logger.error(
                "webhook_function_call_missing_tenant_id",
                message_type=message_type,
                payload=json.dumps(data, indent=2)[:500]
            )
            return {
                "error": "Missing tenant_id in metadata"
            }

        # Process function call
        vapi_service = VAPIService(db)
        result = await vapi_service.handle_function_call(data, tenant_id)

        logger.info(
            "webhook_function_call_success",
            tenant_id=tenant_id,
            function_name=data.get("functionCall", {}).get("name"),
            result_type=type(result).__name__,
            result_preview=str(result)[:200]
        )

        # VAPI expects the result directly, not wrapped in {"result": ...}
        # The result should be a JSON-serializable dict or string
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "webhook_function_call_error",
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


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
    try:
        data = await request.json()
        call_service = CallService(db)
        call = await call_service.handle_call_ended(data)
        logger.info(
            "webhook_call_ended_processed",
            call_id=str(call.id) if call else None,
        )
        return {"status": "processed"}
    except Exception as e:
        logger.error("webhook_call_ended_error", error=str(e))
        return {"status": "error", "detail": str(e)}


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
