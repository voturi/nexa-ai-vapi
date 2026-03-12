"""Call service."""
import uuid
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
import structlog

import app.models  # noqa: F401 — ensures all FK targets are registered
from app.models.call import Call

logger = structlog.get_logger()


class CallService:
    """Service for call operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[Call]:
        """List calls for a tenant."""
        query = select(Call).where(Call.tenant_id == tenant_id)
        if status:
            query = query.where(Call.status == status)
        query = query.offset(skip).limit(limit).order_by(Call.created_at.desc())
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_by_id(self, call_id: UUID) -> Optional[Call]:
        """Get call by ID."""
        result = await self.db.execute(select(Call).where(Call.id == call_id))
        return result.scalar_one_or_none()

    async def get_by_vapi_call_id(self, vapi_call_id: str) -> Optional[Call]:
        """Get call by VAPI call ID."""
        result = await self.db.execute(
            select(Call).where(Call.vapi_call_id == vapi_call_id)
        )
        return result.scalar_one_or_none()

    async def create_from_call_started(
        self,
        tenant_id: str,
        vapi_call_id: str,
        caller_phone: Optional[str] = None,
    ) -> Call:
        """Create a call record when a call starts."""
        call = Call(
            tenant_id=uuid.UUID(tenant_id),
            vapi_call_id=vapi_call_id,
            caller_phone=caller_phone,
            status="in_progress",
            started_at=datetime.utcnow(),
        )
        self.db.add(call)
        await self.db.commit()
        await self.db.refresh(call)
        logger.info("call_record_created", call_id=str(call.id), vapi_call_id=vapi_call_id)
        return call

    async def handle_call_ended(self, data: dict) -> Optional[Call]:
        """
        Handle end-of-call-report from VAPI.

        Real VAPI payload structure (fields are on message, not message.call):
          data["message"]["type"]          == "end-of-call-report"
          data["message"]["call"]["id"]    — vapi call id
          data["message"]["startedAt"]     — ISO timestamp
          data["message"]["endedAt"]       — ISO timestamp
          data["message"]["durationSeconds"]
          data["message"]["transcript"]
          data["message"]["summary"]
          data["message"]["analysis"]
          data["message"]["cost"]
          data["message"]["recordingUrl"]
          data["message"]["customer"]["number"]
          data["message"]["assistant"]["metadata"]["tenant_id"]
        """
        message = data.get("message", {})
        call_obj = message.get("call", {}) or {}
        vapi_call_id = call_obj.get("id")

        if not vapi_call_id:
            logger.warning("call_ended_missing_vapi_call_id")
            return None

        # Look up existing call record
        call = await self.get_by_vapi_call_id(vapi_call_id)

        # Parse timestamps — they're on message, not message.call
        started_at = None
        ended_at = None

        started_str = message.get("startedAt")
        ended_str = message.get("endedAt")

        if started_str:
            try:
                started_at = datetime.fromisoformat(started_str.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                pass

        if ended_str:
            try:
                ended_at = datetime.fromisoformat(ended_str.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                pass

        # Use VAPI's pre-calculated duration if available
        duration_seconds = message.get("durationSeconds")
        if duration_seconds is None and started_at and ended_at:
            duration_seconds = int((ended_at - started_at).total_seconds())

        # Cost is on message directly
        cost_cents = None
        cost = message.get("cost")
        if cost is not None:
            try:
                cost_cents = int(float(cost) * 100)
            except Exception:
                pass

        # Extract analysis, transcript, recording
        analysis = message.get("analysis") or {}
        summary = message.get("summary") or (analysis.get("summary") if analysis else None)
        sentiment = (analysis.get("successEvaluation") or analysis.get("sentiment")) if analysis else None
        transcript = message.get("transcript")
        recording_url = message.get("recordingUrl")

        if call:
            # Update existing record
            call.status = "ended"
            call.ended_at = ended_at or datetime.utcnow()
            call.started_at = call.started_at or started_at
            call.duration_seconds = duration_seconds
            call.transcript = transcript
            call.recording_url = recording_url
            call.summary = summary
            call.sentiment = sentiment
            call.cost_cents = cost_cents
        else:
            # No existing record — extract tenant_id and create one
            # Try assistant metadata (most reliable in real VAPI payloads)
            assistant = message.get("assistant") or {}
            tenant_id = (assistant.get("metadata") or {}).get("tenant_id")

            # Fallback: call.assistant.metadata
            if not tenant_id:
                call_assistant = call_obj.get("assistant") or {}
                tenant_id = (call_assistant.get("metadata") or {}).get("tenant_id")

            # Fallback: call.metadata
            if not tenant_id:
                tenant_id = (call_obj.get("metadata") or {}).get("tenant_id")

            if not tenant_id:
                logger.warning("call_ended_missing_tenant_id", vapi_call_id=vapi_call_id)
                return None

            # caller phone is on message.customer
            caller_phone = (message.get("customer") or {}).get("number")

            call = Call(
                tenant_id=uuid.UUID(tenant_id),
                vapi_call_id=vapi_call_id,
                caller_phone=caller_phone,
                status="ended",
                started_at=started_at,
                ended_at=ended_at or datetime.utcnow(),
                duration_seconds=duration_seconds,
                transcript=transcript,
                recording_url=recording_url,
                summary=summary,
                sentiment=sentiment,
                cost_cents=cost_cents,
            )
            self.db.add(call)

        await self.db.commit()
        await self.db.refresh(call)

        logger.info(
            "call_record_saved",
            call_id=str(call.id),
            vapi_call_id=vapi_call_id,
            duration_seconds=duration_seconds,
            has_transcript=bool(transcript),
        )
        return call

    async def handle_call_status(self, data: dict):
        """Handle call status webhook — update status field."""
        call_obj = data.get("call", {}) or {}
        vapi_call_id = call_obj.get("id")
        status = data.get("status") or call_obj.get("status")

        if not vapi_call_id or not status:
            return

        call = await self.get_by_vapi_call_id(vapi_call_id)
        if call:
            call.status = status
            await self.db.commit()
            logger.info("call_status_updated", vapi_call_id=vapi_call_id, status=status)
