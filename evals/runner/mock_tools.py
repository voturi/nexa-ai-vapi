"""
Mock tool executor for eval runs.

Provides configurable responses for all tools.
Case-specific overrides take precedence; sensible defaults apply otherwise.
For Phase 3 (Suite F — Tool Failure), override with error responses.
"""
from __future__ import annotations

from typing import Any

from evals.schema.case import EvalCase

_DEFAULTS: dict[str, dict[str, Any]] = {
    "check_availability": {
        "available": True,
        "slots": ["9:00 AM", "10:00 AM", "11:00 AM", "2:00 PM", "3:00 PM"],
        "date": "tomorrow",
        "message": "Several slots available",
    },
    "create_booking": {
        "booking_id": "mock_booking_001",
        "status": "confirmed",
        "scheduled_at": "tomorrow at 10:00 AM",
        "confirmation_number": "BK-001",
    },
    "cancel_booking": {
        "status": "cancelled",
        "booking_id": "mock_booking_001",
        "message": "Appointment successfully cancelled",
    },
    "reschedule_booking": {
        "status": "confirmed",
        "booking_id": "mock_booking_001",
        "new_scheduled_at": "Friday at 10:00 AM",
    },
    "create_lead": {
        "lead_id": "mock_lead_001",
        "status": "created",
        "message": "Message recorded — team will follow up",
    },
    "get_operating_hours": {
        "monday_friday": "7:00 AM - 6:00 PM",
        "saturday": "8:00 AM - 2:00 PM",
        "sunday": "Closed",
        "emergency_after_hours": True,
    },
    "update_contact": {
        "status": "updated",
        "contact_id": "mock_contact_001",
    },
}

# Standard tool failure response — used by Suite F cases
TOOL_UNAVAILABLE: dict[str, Any] = {
    "error": "service_unavailable",
    "message": "Unable to complete request at this time. Please try again shortly.",
}

TOOL_TIMEOUT: dict[str, Any] = {
    "error": "timeout",
    "message": "The request timed out.",
}


class MockToolExecutor:
    """
    Executes tool calls with configurable responses.

    Usage:
        executor = MockToolExecutor(case)
        result = executor.execute("create_booking", {"service_id": "haircut", ...})
    """

    def __init__(self, case: EvalCase):
        # Build lookup from case-level overrides
        self._overrides: dict[str, dict[str, Any]] = {
            r.tool_name: r.response
            for r in case.mock_tool_responses
        }

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Return the configured response for this tool call."""
        if tool_name in self._overrides:
            return self._overrides[tool_name]
        return _DEFAULTS.get(tool_name, {"status": "success"})
