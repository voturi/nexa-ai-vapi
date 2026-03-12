"""
Replay runner — Phase 1 (transcript mode).

Feeds caller turns through the skills engine + Claude directly,
mocking all tool calls via MockToolExecutor.

Does NOT require a database connection.
Requires ANTHROPIC_API_KEY in environment.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Optional

import anthropic

# Ensure the backend package is importable when running from the evals directory
_BACKEND_ROOT = Path(__file__).parent.parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.services.skills_engine import SkillsEngine  # noqa: E402
from evals.runner.mock_tools import MockToolExecutor  # noqa: E402
from evals.schema.case import ConversationTurn, EvalCase, EvalTrace  # noqa: E402

# ---------------------------------------------------------------------------
# Tool definitions registered with Claude during eval runs.
# Mirrors the tools registered with VAPI in production.
# ---------------------------------------------------------------------------

EVAL_TOOLS: list[dict[str, Any]] = [
    {
        "name": "check_availability",
        "description": "Check available appointment slots for a service on a given date.",
        "input_schema": {
            "type": "object",
            "properties": {
                "service_id": {"type": "string", "description": "The service identifier"},
                "preferred_date": {"type": "string", "description": "Preferred date (e.g. 'tomorrow', 'next Friday')"},
            },
            "required": ["service_id", "preferred_date"],
        },
    },
    {
        "name": "create_booking",
        "description": "Create a confirmed appointment booking.",
        "input_schema": {
            "type": "object",
            "properties": {
                "service_id": {"type": "string"},
                "datetime": {"type": "string", "description": "Confirmed date and time"},
                "customer_name": {"type": "string"},
                "customer_phone": {"type": "string"},
                "customer_email": {"type": "string"},
                "notes": {"type": "string"},
            },
            "required": ["service_id", "datetime", "customer_name", "customer_phone"],
        },
    },
    {
        "name": "cancel_booking",
        "description": "Cancel an existing appointment.",
        "input_schema": {
            "type": "object",
            "properties": {
                "booking_id": {"type": "string"},
                "customer_name": {"type": "string"},
                "customer_phone": {"type": "string"},
                "date": {"type": "string", "description": "Approximate date of the appointment to cancel"},
                "reason": {"type": "string"},
            },
            "required": [],
        },
    },
    {
        "name": "create_lead",
        "description": "Record a lead or message for follow-up by the team.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string"},
                "customer_phone": {"type": "string"},
                "customer_email": {"type": "string"},
                "notes": {"type": "string", "description": "Summary of the enquiry or message"},
                "interest_level": {
                    "type": "string",
                    "enum": ["hot", "warm", "cold"],
                },
            },
            "required": ["customer_name", "customer_phone"],
        },
    },
    {
        "name": "get_operating_hours",
        "description": "Retrieve the business operating hours.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


def _content_blocks_to_dicts(blocks: list[Any]) -> list[dict[str, Any]]:
    """Convert Anthropic SDK content blocks to plain dicts for the next API call."""
    result = []
    for block in blocks:
        if block.type == "text":
            result.append({"type": "text", "text": block.text})
        elif block.type == "tool_use":
            result.append({
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input,
            })
    return result


class ReplayRunner:
    """
    Runs a single EvalCase through the skills engine + Claude.

    Each caller turn is fed to Claude in sequence.
    Tool calls are intercepted and served by MockToolExecutor.
    The resulting EvalTrace captures everything the agent did.
    """

    def __init__(
        self,
        skills_base_path: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-6",
    ):
        _skills_path = skills_base_path or str(_BACKEND_ROOT / "skills")
        self.skills_engine = SkillsEngine(base_path=_skills_path)
        self.client = anthropic.Anthropic(
            api_key=anthropic_api_key or os.environ["ANTHROPIC_API_KEY"]
        )
        self.model = model

    def run(self, case: EvalCase) -> EvalTrace:
        """Run a case and return the captured trace. Never raises — errors are stored in trace."""
        start = time.monotonic()
        try:
            return self._run_case(case, start)
        except Exception as exc:
            return EvalTrace(
                case_id=case.case_id,
                error=str(exc),
                duration_ms=int((time.monotonic() - start) * 1000),
            )

    # ── Internal ─────────────────────────────────────────────────────────────

    def _run_case(self, case: EvalCase, start: float) -> EvalTrace:
        tool_executor = MockToolExecutor(case)
        tc = case.tenant_config

        system_prompt = self.skills_engine.build_system_prompt(
            vertical=tc.get("vertical", "smb_general"),
            integrations=list(tc.get("integrations", {}).keys()),
            tenant_config=tc,
        )

        trace = EvalTrace(case_id=case.case_id)
        messages: list[dict[str, Any]] = []
        tools_called: list[str] = []
        tool_arguments: list[dict[str, Any]] = []

        for caller_text in case.caller_turns:
            messages.append({"role": "user", "content": caller_text})
            trace.conversation.append(ConversationTurn(role="caller", text=caller_text))

            agent_text = self._run_agent_turn(
                messages=messages,
                system_prompt=system_prompt,
                tool_executor=tool_executor,
                tools_called=tools_called,
                tool_arguments=tool_arguments,
            )

            trace.conversation.append(ConversationTurn(role="agent", text=agent_text))
            trace.agent_turns.append(agent_text)

        trace.tools_called = tools_called
        trace.tool_arguments = tool_arguments
        trace.duration_ms = int((time.monotonic() - start) * 1000)

        # Extract structured signal from the run
        trace.inferred_intent = self._extract_intent(trace)
        trace.extracted_slots = self._extract_slots(trace)
        trace.final_outcome = self._infer_outcome(trace)

        return trace

    def _run_agent_turn(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str,
        tool_executor: MockToolExecutor,
        tools_called: list[str],
        tool_arguments: list[dict[str, Any]],
    ) -> str:
        """
        Run one agent turn, handling tool-use loops.

        Mutates `messages` in-place so the full history (including tool exchanges)
        is preserved for subsequent turns.
        Returns the final text response.
        """
        while True:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system_prompt,
                tools=EVAL_TOOLS,
                messages=messages,
            )

            if response.stop_reason == "tool_use":
                # Append assistant message with tool_use blocks
                assistant_content = _content_blocks_to_dicts(response.content)
                messages.append({"role": "assistant", "content": assistant_content})

                # Execute each tool and collect results
                tool_results: list[dict[str, Any]] = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = tool_executor.execute(block.name, block.input)
                        tools_called.append(block.name)
                        tool_arguments.append({"tool": block.name, "args": block.input})
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result),
                        })

                messages.append({"role": "user", "content": tool_results})
                continue  # Let Claude continue after seeing the tool results

            # End of turn — extract text
            text_parts = [
                block.text
                for block in response.content
                if block.type == "text"
            ]
            final_text = " ".join(text_parts).strip()
            messages.append({"role": "assistant", "content": final_text})
            return final_text

    # ── Signal extraction ─────────────────────────────────────────────────────

    def _extract_intent(self, trace: EvalTrace) -> Optional[str]:
        """
        Derive intent from tools called (highest signal) then fallback to
        keyword scan of agent turns.

        Phase 2 will replace the keyword fallback with structured output
        directly from the agent (inferred_intent logged per turn).
        """
        tool_set = set(trace.tools_called)

        if "create_booking" in tool_set:
            return "create_booking"
        if "cancel_booking" in tool_set:
            return "cancel_booking"
        if "create_lead" in tool_set:
            # Distinguish leave_message from request_quote by context
            combined = " ".join(trace.agent_turns).lower()
            if any(w in combined for w in ["quote", "price", "cost", "estimate", "fee"]):
                return "request_quote"
            return "leave_message"
        if "check_availability" in tool_set and "create_booking" not in tool_set:
            return "check_availability"
        if "get_operating_hours" in tool_set:
            return "get_operating_hours"

        # Keyword fallback on agent responses
        combined = " ".join(trace.agent_turns).lower()
        if any(w in combined for w in ["booked", "scheduled", "appointment confirmed", "confirmed your booking"]):
            return "create_booking"
        if any(w in combined for w in ["rescheduled", "moved your appointment", "new time"]):
            return "reschedule_booking"
        if any(w in combined for w in ["cancelled", "cancellation confirmed"]):
            return "cancel_booking"
        if any(w in combined for w in ["passed on", "message for", "note that", "let them know", "will be in touch"]):
            return "leave_message"
        if any(w in combined for w in ["quote", "pricing", "cost depends", "give you a call"]):
            return "request_quote"
        if any(w in combined for w in ["open", "hours", "monday", "saturday", "closed sunday"]):
            return "get_operating_hours"

        return None

    def _extract_slots(self, trace: EvalTrace) -> dict[str, str]:
        """
        Extract slots from tool call arguments (most reliable source).
        Phase 2 will add per-turn structured slot logging.
        """
        slots: dict[str, str] = {}
        for tool_call in trace.tool_arguments:
            args = tool_call.get("args", {})
            if args.get("customer_name"):
                slots["customer_name"] = args["customer_name"]
            if args.get("customer_phone"):
                slots["customer_phone"] = args["customer_phone"]
            if args.get("customer_email"):
                slots["customer_email"] = args["customer_email"]
            if args.get("service_id"):
                slots["service"] = args["service_id"]
            if args.get("datetime"):
                slots["datetime"] = args["datetime"]
            if args.get("preferred_date"):
                slots["date"] = args["preferred_date"]
            if args.get("notes"):
                slots["notes"] = args["notes"]
            if args.get("date"):
                slots["date"] = args["date"]
        return slots

    def _infer_outcome(self, trace: EvalTrace) -> Optional[str]:
        """
        Map tools called and agent text to a terminal outcome string.

        Rule: booking/cancellation outcomes are ONLY inferred from tool calls,
        never from keyword matching. This prevents false positives where
        availability confirmations or check responses are mistaken for a booking.

        Informational outcomes (hours, quotes) have no tool call, so keyword
        matching is appropriate there.
        """
        tool_set = set(trace.tools_called)

        # Tool-authoritative outcomes — only set when the action actually happened
        if "create_booking" in tool_set:
            return "booking_confirmed"
        if "cancel_booking" in tool_set:
            return "booking_cancelled"
        if "create_lead" in tool_set:
            combined = " ".join(trace.agent_turns).lower()
            if any(w in combined for w in ["quote", "price", "estimate", "fee", "cost"]):
                return "lead_created"  # maps to quote_provided via outcome aliases
            return "message_taken"
        if "get_operating_hours" in tool_set:
            return "hours_provided"

        # Keyword fallback for informational intents only (no tool call expected)
        combined = " ".join(trace.agent_turns).lower()
        if any(w in combined for w in ["hours", "open until", "closed on", "monday to friday", "we are open"]):
            return "hours_provided"
        if any(w in combined for w in ["message", "pass on", "let them know", "pass that on", "will be in touch"]):
            return "message_taken"

        return "unknown"
