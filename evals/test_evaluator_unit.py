"""
Unit tests for RuleBasedEvaluator — no API key required.

These verify scoring logic using hand-crafted EvalTrace objects.
Always runs as part of the standard pytest suite.
"""
from __future__ import annotations

import pytest

from evals.evaluators.rule_based import RuleBasedEvaluator
from evals.schema.case import (
    DimensionScore,
    EvalCase,
    EvalTrace,
    GroundTruth,
    MockToolResponse,
    RiskTier,
    SuccessCriteria,
)

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_tenant() -> dict:
    return {
        "business_name": "Test Business",
        "vertical": "tradies",
        "phone": "+61 2 0000 0000",
        "timezone": "Australia/Sydney",
        "services": [{"id": "routine_maintenance", "name": "Routine Maintenance", "duration_minutes": 60}],
        "integrations": {},
    }


def _booking_case(
    intent: str = "create_booking",
    expected_tools: list[str] | None = None,
    expected_outcome: str = "booking_confirmed",
    slots: dict | None = None,
    must_call_expected_tools: bool = False,
) -> EvalCase:
    return EvalCase(
        case_id="test_booking_001",
        description="Test case",
        business_domain="tradies",
        scenario_type="appointment_booking",
        priority="high",
        risk_tier=RiskTier.P1,
        caller_turns=["I need a plumber tomorrow"],
        ground_truth=GroundTruth(
            intent=intent,
            slots=slots or {"service": "routine_maintenance", "date": "tomorrow"},
            expected_tools=expected_tools or ["check_availability", "create_booking"],
            expected_outcome=expected_outcome,
        ),
        success_criteria=SuccessCriteria(
            must_capture_intent=True,
            must_not_hallucinate_slots=True,
            must_complete_task=True,
            must_call_expected_tools=must_call_expected_tools,
        ),
        tenant_config=_minimal_tenant(),
    )


def _trace(
    intent: str | None = "create_booking",
    slots: dict | None = None,
    tools: list[str] | None = None,
    outcome: str | None = "booking_confirmed",
) -> EvalTrace:
    return EvalTrace(
        case_id="test_booking_001",
        inferred_intent=intent,
        extracted_slots=slots or {"service": "routine_maintenance", "date": "tomorrow"},
        tools_called=tools or ["check_availability", "create_booking"],
        final_outcome=outcome,
    )


# ---------------------------------------------------------------------------
# Intent scoring
# ---------------------------------------------------------------------------

class TestIntentScoring:
    def test_exact_match_scores_3(self):
        ev = RuleBasedEvaluator()
        case = _booking_case()
        t = _trace(intent="create_booking")
        result = ev.evaluate(case, t)
        assert result.intent_score.score == 3.0
        assert result.intent_score.passed_gate is True

    def test_wrong_intent_scores_0(self):
        ev = RuleBasedEvaluator()
        case = _booking_case()
        t = _trace(intent="get_operating_hours")
        result = ev.evaluate(case, t)
        assert result.intent_score.score == 0.0
        assert result.intent_score.passed_gate is False

    def test_related_intent_scores_partial(self):
        ev = RuleBasedEvaluator()
        case = _booking_case(intent="create_booking")
        t = _trace(intent="check_availability")  # same booking family
        result = ev.evaluate(case, t)
        assert 1.0 <= result.intent_score.score < 3.0

    def test_none_intent_scores_0(self):
        ev = RuleBasedEvaluator()
        case = _booking_case()
        t = _trace(intent=None)
        result = ev.evaluate(case, t)
        assert result.intent_score.score == 0.0


# ---------------------------------------------------------------------------
# Slot scoring
# ---------------------------------------------------------------------------

class TestSlotScoring:
    def test_all_slots_correct_scores_3(self):
        ev = RuleBasedEvaluator()
        case = _booking_case(slots={"service": "routine_maintenance", "date": "tomorrow"})
        t = _trace(slots={"service": "routine_maintenance", "date": "tomorrow"})
        result = ev.evaluate(case, t)
        assert result.slot_score.score == 3.0

    def test_missing_slot_reduces_score(self):
        ev = RuleBasedEvaluator()
        case = _booking_case(slots={"service": "routine_maintenance", "date": "tomorrow"})
        t = _trace(slots={"service": "routine_maintenance"})  # date missing
        result = ev.evaluate(case, t)
        assert result.slot_score.score < 3.0
        assert result.slot_score.passed_gate is False

    def test_no_slots_required_scores_3(self):
        ev = RuleBasedEvaluator()
        case = _booking_case(slots={})
        t = _trace(slots={})
        result = ev.evaluate(case, t)
        assert result.slot_score.score == 3.0

    def test_hallucinated_slot_triggers_gate(self):
        ev = RuleBasedEvaluator()
        case = _booking_case(slots={"service": "routine_maintenance"})
        t = _trace(slots={"service": "routine_maintenance", "unexpected_field": "xyz"})
        result = ev.evaluate(case, t)
        assert result.hard_gate_results.get("no_hallucinated_slots") is False


# ---------------------------------------------------------------------------
# Tool scoring
# ---------------------------------------------------------------------------

class TestToolScoring:
    def test_all_tools_called_scores_3(self):
        ev = RuleBasedEvaluator()
        case = _booking_case(expected_tools=["check_availability", "create_booking"])
        t = _trace(tools=["check_availability", "create_booking"])
        result = ev.evaluate(case, t)
        assert result.tool_score.score == 3.0

    def test_missing_tool_reduces_score(self):
        ev = RuleBasedEvaluator()
        case = _booking_case(expected_tools=["check_availability", "create_booking"])
        t = _trace(tools=["create_booking"])  # check_availability skipped
        result = ev.evaluate(case, t)
        assert result.tool_score.score < 3.0

    def test_strict_tool_gate_fails_on_missing(self):
        ev = RuleBasedEvaluator()
        case = _booking_case(
            expected_tools=["check_availability", "create_booking"],
            must_call_expected_tools=True,
        )
        t = _trace(tools=["create_booking"])
        result = ev.evaluate(case, t)
        assert result.hard_gate_results["tools_correct"] is False
        assert result.passed is False

    def test_extra_tools_reduces_score_slightly(self):
        ev = RuleBasedEvaluator()
        case = _booking_case(expected_tools=["check_availability", "create_booking"])
        t = _trace(tools=["check_availability", "create_booking", "create_lead"])
        result = ev.evaluate(case, t)
        # Required tools present — passes gate but score slightly below 3.0
        assert result.tool_score.passed_gate is True
        assert result.tool_score.score <= 3.0

    def test_no_tools_required_scores_3(self):
        ev = RuleBasedEvaluator()
        case = _booking_case(expected_tools=[])
        t = _trace(tools=[])
        result = ev.evaluate(case, t)
        assert result.tool_score.score == 3.0


# ---------------------------------------------------------------------------
# Outcome scoring
# ---------------------------------------------------------------------------

class TestOutcomeScoring:
    def test_correct_outcome_scores_3(self):
        ev = RuleBasedEvaluator()
        case = _booking_case(expected_outcome="booking_confirmed")
        t = _trace(outcome="booking_confirmed")
        result = ev.evaluate(case, t)
        assert result.outcome_score.score == 3.0

    def test_outcome_alias_accepted(self):
        ev = RuleBasedEvaluator()
        case = _booking_case(expected_outcome="booking_confirmed")
        t = _trace(outcome="appointment_confirmed")  # alias
        result = ev.evaluate(case, t)
        assert result.outcome_score.score == 3.0

    def test_unknown_outcome_scores_0(self):
        ev = RuleBasedEvaluator()
        case = _booking_case(expected_outcome="booking_confirmed")
        t = _trace(outcome="unknown")
        result = ev.evaluate(case, t)
        assert result.outcome_score.score == 0.0


# ---------------------------------------------------------------------------
# Overall pass/fail logic
# ---------------------------------------------------------------------------

class TestOverallPassFail:
    def test_all_gates_pass_means_overall_pass(self):
        ev = RuleBasedEvaluator()
        case = _booking_case()
        t = _trace()
        result = ev.evaluate(case, t)
        assert result.passed is True

    def test_intent_fail_means_overall_fail(self):
        ev = RuleBasedEvaluator()
        case = _booking_case()
        t = _trace(intent="get_operating_hours")
        result = ev.evaluate(case, t)
        assert result.passed is False

    def test_task_not_complete_means_overall_fail(self):
        ev = RuleBasedEvaluator()
        case = _booking_case()
        t = _trace(outcome="unknown")
        result = ev.evaluate(case, t)
        assert result.passed is False

    def test_runner_error_always_fails(self):
        ev = RuleBasedEvaluator()
        case = _booking_case()
        error_trace = EvalTrace(case_id="test_booking_001", error="Connection refused")
        result = ev.evaluate(case, error_trace)
        assert result.passed is False
        assert "Runner error" in result.errors[0]

    def test_p1_case_with_error_hard_fails(self):
        ev = RuleBasedEvaluator()
        case = _booking_case()
        assert case.risk_tier == RiskTier.P1
        t = _trace(intent="wrong_intent")
        result = ev.evaluate(case, t)
        assert result.passed is False


# ---------------------------------------------------------------------------
# Composite score
# ---------------------------------------------------------------------------

class TestCompositeScore:
    def test_perfect_run_composite_is_3(self):
        ev = RuleBasedEvaluator()
        case = _booking_case(slots={}, expected_tools=[])
        t = _trace(slots={}, tools=[], outcome="booking_confirmed")
        result = ev.evaluate(case, t)
        assert result.composite_score == pytest.approx(3.0, abs=0.1)

    def test_composite_is_average_of_four_dimensions(self):
        ev = RuleBasedEvaluator()
        case = _booking_case()
        t = _trace()
        result = ev.evaluate(case, t)
        expected = (
            result.intent_score.score
            + result.slot_score.score
            + result.tool_score.score
            + result.outcome_score.score
        ) / 4.0
        assert result.composite_score == pytest.approx(expected, abs=0.01)
