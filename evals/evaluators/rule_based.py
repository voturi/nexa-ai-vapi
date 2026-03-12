"""
Rule-based evaluator — Phase 1 hard gates and dimension scoring.

Scoring model:
    Interaction Quality = Safety Gates × Outcome Score × Experience Modifier

Phase 1 covers Safety Gates + Outcome Score (intent, slot, tool, task completion).
Experience Modifier is added in Phase 5 via LLM judge.

Dimension scores (0–3):
    0 = wrong / missing
    1 = partial / related but incorrect
    2 = mostly correct, minor issue
    3 = fully correct
"""
from __future__ import annotations

from typing import Optional

from evals.schema.case import (
    DimensionScore,
    EvalCase,
    EvalResult,
    EvalTrace,
    RiskTier,
)

# Intent families for partial-credit matching
_BOOKING_INTENTS = {"create_booking", "check_availability", "reschedule_booking"}
_CANCELLATION_INTENTS = {"cancel_booking"}
_INFO_INTENTS = {"get_operating_hours", "request_quote"}
_LEAD_INTENTS = {"leave_message", "create_lead", "request_quote"}

_INTENT_FAMILIES: list[set[str]] = [
    _BOOKING_INTENTS,
    _CANCELLATION_INTENTS,
    _INFO_INTENTS,
    _LEAD_INTENTS,
]

# Outcome aliases — e.g. "booking_confirmed" and "create_booking" are the same business result
_OUTCOME_ALIASES: dict[str, list[str]] = {
    "booking_confirmed": ["booking_confirmed", "create_booking", "appointment_confirmed"],
    "booking_cancelled": ["booking_cancelled", "cancel_booking", "cancellation_confirmed"],
    "lead_created": ["lead_created", "create_lead", "message_taken", "callback_requested"],
    "message_taken": ["message_taken", "lead_created", "create_lead"],
    "hours_provided": ["hours_provided", "get_operating_hours", "information_provided"],
    "quote_provided": ["quote_provided", "request_quote", "lead_created"],
}


class RuleBasedEvaluator:
    """
    Deterministic evaluator for Phase 1.

    Evaluates intent, slots, tools, and task outcome.
    Does not require an API key or external service.
    """

    def evaluate(self, case: EvalCase, trace: EvalTrace) -> EvalResult:
        errors: list[str] = []
        notes: list[str] = []
        hard_gate_results: dict[str, bool] = {}

        # If the runner itself failed, short-circuit to a failed result
        if trace.error:
            return self._runner_error_result(case, trace)

        # ── Hard Gates ────────────────────────────────────────────────────

        # Gate: intent captured correctly
        intent_ok = self._intent_matches(case.ground_truth.intent, trace.inferred_intent)
        hard_gate_results["intent_captured"] = intent_ok
        if not intent_ok and case.success_criteria.must_capture_intent:
            errors.append(
                f"Intent mismatch — expected '{case.ground_truth.intent}', "
                f"got '{trace.inferred_intent}'"
            )

        # Gate: no hallucinated slots (slots agent filled that weren't asked for)
        hallucinated = self._find_hallucinated_slots(
            expected=case.ground_truth.slots,
            actual=trace.extracted_slots,
        )
        no_hallucination = len(hallucinated) == 0
        hard_gate_results["no_hallucinated_slots"] = no_hallucination
        if not no_hallucination and case.success_criteria.must_not_hallucinate_slots:
            errors.append(f"Hallucinated slots: {hallucinated}")

        # Gate: task completed (outcome matches expected)
        task_complete = self._outcome_matches(
            expected=case.ground_truth.expected_outcome,
            actual=trace.final_outcome,
        )
        hard_gate_results["task_completed"] = task_complete
        if not task_complete and case.success_criteria.must_complete_task:
            errors.append(
                f"Task not completed — expected outcome '{case.ground_truth.expected_outcome}', "
                f"got '{trace.final_outcome}'"
            )

        # Gate: expected tools called (strict mode, off by default)
        tools_ok = self._tools_correct(
            expected=case.ground_truth.expected_tools,
            actual=trace.tools_called,
        )
        hard_gate_results["tools_correct"] = tools_ok
        if not tools_ok and case.success_criteria.must_call_expected_tools:
            errors.append(
                f"Tool sequence mismatch — expected {case.ground_truth.expected_tools}, "
                f"got {trace.tools_called}"
            )

        # ── Dimension Scores (0–3) ────────────────────────────────────────

        intent_score = self._score_intent(case, trace)
        slot_score = self._score_slots(case, trace)
        tool_score = self._score_tools(case, trace)
        outcome_score = self._score_outcome(case, trace)

        composite = (
            intent_score.score
            + slot_score.score
            + tool_score.score
            + outcome_score.score
        ) / 4.0

        # ── Overall pass/fail ─────────────────────────────────────────────

        active_gates = {
            "intent_captured": case.success_criteria.must_capture_intent,
            "no_hallucinated_slots": case.success_criteria.must_not_hallucinate_slots,
            "task_completed": case.success_criteria.must_complete_task,
            "tools_correct": case.success_criteria.must_call_expected_tools,
        }
        passed = all(
            hard_gate_results[gate]
            for gate, required in active_gates.items()
            if required
        )

        # P0 / P1 cases with errors are always a hard fail
        if case.risk_tier in (RiskTier.P0, RiskTier.P1) and errors:
            passed = False

        return EvalResult(
            case_id=case.case_id,
            business_domain=case.business_domain,
            scenario_type=case.scenario_type,
            risk_tier=case.risk_tier,
            passed=passed,
            hard_gate_results=hard_gate_results,
            intent_score=intent_score,
            slot_score=slot_score,
            tool_score=tool_score,
            outcome_score=outcome_score,
            composite_score=round(composite, 2),
            errors=errors,
            notes=notes,
        )

    # ── Intent ──────────────────────────────────────────────────────────────

    def _intent_matches(self, expected: str, actual: Optional[str]) -> bool:
        if not actual:
            return False
        return expected.lower().strip() == actual.lower().strip()

    def _intents_related(self, a: str, b: str) -> bool:
        """True if both intents belong to the same family."""
        for family in _INTENT_FAMILIES:
            if a in family and b in family:
                return True
        return False

    def _score_intent(self, case: EvalCase, trace: EvalTrace) -> DimensionScore:
        expected = case.ground_truth.intent
        actual = trace.inferred_intent

        if self._intent_matches(expected, actual):
            return DimensionScore(score=3.0, passed_gate=True, notes="Exact match")

        if not actual:
            return DimensionScore(score=0.0, passed_gate=False, notes="No intent extracted")

        if self._intents_related(expected, actual):
            return DimensionScore(
                score=1.5,
                passed_gate=False,
                notes=f"Related family but wrong intent: expected '{expected}', got '{actual}'",
            )

        return DimensionScore(
            score=0.0,
            passed_gate=False,
            notes=f"Wrong intent: expected '{expected}', got '{actual}'",
        )

    # ── Slots ────────────────────────────────────────────────────────────────

    def _find_hallucinated_slots(
        self, expected: dict[str, str], actual: dict[str, str]
    ) -> list[str]:
        """
        Slots filled by the agent that were not in the ground truth.
        Only flags clearly unexpected slots; common safe slots are allowed.
        """
        # These slots are always acceptable to collect even if not in ground truth
        _always_allowed = {
            "customer_name", "customer_phone", "customer_email", "notes",
            "service", "service_id", "date", "time", "datetime",
        }
        expected_keys = set(expected.keys())
        actual_keys = set(actual.keys())
        unexpected = actual_keys - expected_keys - _always_allowed
        return list(unexpected)

    def _slot_value_matches(self, expected: str, actual: str) -> bool:
        """Loose match — normalise and check containment."""
        e = expected.lower().strip()
        a = actual.lower().strip()
        return e in a or a in e

    def _score_slots(self, case: EvalCase, trace: EvalTrace) -> DimensionScore:
        expected = case.ground_truth.slots
        actual = trace.extracted_slots

        if not expected:
            return DimensionScore(score=3.0, passed_gate=True, notes="No slots required")

        required = set(expected.keys())
        captured = set(actual.keys())
        captured_required = required & captured
        coverage = len(captured_required) / len(required)

        if coverage == 0:
            return DimensionScore(
                score=0.0,
                passed_gate=False,
                notes=f"No required slots captured. Expected: {required}",
            )

        if coverage < 1.0:
            missing = required - captured
            return DimensionScore(
                score=round(coverage * 2.0, 1),
                passed_gate=False,
                notes=f"Missing slots: {missing}",
            )

        # All required slots present — now check values
        value_correct = sum(
            1 for k in required
            if k in actual and self._slot_value_matches(expected[k], actual[k])
        )
        value_ratio = value_correct / len(required)

        if value_ratio == 1.0:
            return DimensionScore(score=3.0, passed_gate=True, notes="All slots correct")

        return DimensionScore(
            score=round(1.0 + value_ratio * 2.0, 1),
            passed_gate=value_ratio >= 0.8,
            notes=f"{value_correct}/{len(required)} slot values matched",
        )

    # ── Tools ────────────────────────────────────────────────────────────────

    def _tools_correct(self, expected: list[str], actual: list[str]) -> bool:
        """All expected tools must have been called (order-insensitive in Phase 1)."""
        return set(expected).issubset(set(actual))

    def _score_tools(self, case: EvalCase, trace: EvalTrace) -> DimensionScore:
        expected = set(case.ground_truth.expected_tools)
        actual = set(trace.tools_called)

        if not expected:
            return DimensionScore(score=3.0, passed_gate=True, notes="No tools required")

        called = expected & actual
        unexpected = actual - expected
        coverage = len(called) / len(expected)

        if coverage == 1.0 and not unexpected:
            return DimensionScore(score=3.0, passed_gate=True, notes="All tools called correctly")

        if coverage == 1.0:
            return DimensionScore(
                score=2.5,
                passed_gate=True,
                notes=f"Required tools all called; unexpected extras: {unexpected}",
            )

        return DimensionScore(
            score=round(coverage * 2.0, 1),
            passed_gate=False,
            notes=f"Called {called}, missed {expected - actual}",
        )

    # ── Outcome ──────────────────────────────────────────────────────────────

    def _outcome_matches(self, expected: str, actual: Optional[str]) -> bool:
        if not actual or not expected:
            return False
        # Direct match
        if expected.lower().strip() == actual.lower().strip():
            return True
        # Alias match
        aliases = _OUTCOME_ALIASES.get(expected, [])
        return actual.lower().strip() in [a.lower() for a in aliases]

    def _score_outcome(self, case: EvalCase, trace: EvalTrace) -> DimensionScore:
        expected = case.ground_truth.expected_outcome
        actual = trace.final_outcome

        if self._outcome_matches(expected, actual):
            return DimensionScore(score=3.0, passed_gate=True, notes="Correct outcome")

        if not actual or actual == "unknown":
            return DimensionScore(score=0.0, passed_gate=False, notes="No outcome detected")

        return DimensionScore(
            score=1.0,
            passed_gate=False,
            notes=f"Wrong outcome: expected '{expected}', got '{actual}'",
        )

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _runner_error_result(self, case: EvalCase, trace: EvalTrace) -> EvalResult:
        zero = DimensionScore(score=0.0, passed_gate=False, notes="Runner error")
        return EvalResult(
            case_id=case.case_id,
            business_domain=case.business_domain,
            scenario_type=case.scenario_type,
            risk_tier=case.risk_tier,
            passed=False,
            hard_gate_results={},
            intent_score=zero,
            slot_score=zero,
            tool_score=zero,
            outcome_score=zero,
            composite_score=0.0,
            errors=[f"Runner error: {trace.error}"],
        )
