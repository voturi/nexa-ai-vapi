"""
Suite B — Critical Precision eval tests (tradies vertical).

Tests phone number formats, AU date/time slang, address/suburb capture,
email formats, and service disambiguation — all with strict critical token
matching via rapidfuzz normalisation + P1 hard gates.

Run:
    # Full report (needs ANTHROPIC_API_KEY)
    pytest evals/test_suite_b.py::test_suite_b_report -v -s

    # Per-category slices
    pytest evals/test_suite_b.py::test_suite_b_phone_precision -v -s
    pytest evals/test_suite_b.py::test_suite_b_email_precision -v -s
    pytest evals/test_suite_b.py::test_suite_b_service_disambiguation -v -s

    # Single case
    pytest evals/test_suite_b.py -k "phone_tradies_001" -v -s

    # Unit test — no API key required
    pytest evals/test_suite_b.py::test_critical_token_evaluator_unit -v
"""
from __future__ import annotations

import pytest
from pathlib import Path

from evals.schema.case import EvalCase
from evals.runner.replay import ReplayRunner
from evals.evaluators.rule_based import RuleBasedEvaluator, CriticalTokenEvaluator
from evals.trace.collector import TraceCollector
from evals.report import print_report, save_results, compare_to_baseline

SUITE_B_DIR = Path(__file__).parent / "cases" / "suite_b_critical_precision"
RESULTS_DIR = Path(__file__).parent / "results"
TRACES_DIR  = Path(__file__).parent / "results" / "traces"


def _load_suite_b() -> list[EvalCase]:
    cases = []
    for path in sorted(SUITE_B_DIR.glob("*.json")):
        cases.append(EvalCase.from_file(path))
    return cases


def _cases_by_tag(tag: str) -> list[EvalCase]:
    return [c for c in _load_suite_b() if tag in c.tags]


# ── Unit test — no API key required ──────────────────────────────────────────

def test_critical_token_evaluator_unit():
    """Verify normalisation and matching logic without hitting the API."""
    evaluator = CriticalTokenEvaluator()

    # Phone — exact match after digit stripping
    passed, failures = evaluator.evaluate_critical_tokens(
        {"customer_phone": "0423456789"},
        {"customer_phone": "0423 456 789"},
    )
    assert passed, f"Expected phone match to pass: {failures}"

    # Phone — international prefix normalisation
    passed, failures = evaluator.evaluate_critical_tokens(
        {"customer_phone": "0423456789"},
        {"customer_phone": "+61 423 456 789"},
    )
    assert passed, f"Expected +61 prefix normalisation to pass: {failures}"

    # Phone — wrong number should fail
    passed, failures = evaluator.evaluate_critical_tokens(
        {"customer_phone": "0423456789"},
        {"customer_phone": "0423456780"},  # last digit wrong
    )
    assert not passed, "Wrong phone number should fail"

    # Email — exact match after lowercase
    passed, failures = evaluator.evaluate_critical_tokens(
        {"customer_email": "john.smith@gmail.com"},
        {"customer_email": "John.Smith@gmail.com"},
    )
    assert passed, f"Expected case-insensitive email match: {failures}"

    # Email — wrong domain should fail
    passed, failures = evaluator.evaluate_critical_tokens(
        {"customer_email": "john.smith@gmail.com"},
        {"customer_email": "john.smith@hotmail.com"},
    )
    assert not passed, "Wrong email domain should fail"

    # Date — fuzzy match
    passed, failures = evaluator.evaluate_critical_tokens(
        {"date": "tomorrow afternoon"},
        {"date": "tomorrow arvo"},
    )
    assert passed, f"Expected 'arvo' fuzzy match to pass: {failures}"

    # Address — fuzzy match
    passed, failures = evaluator.evaluate_critical_tokens(
        {"address": "14 macquarie street parramatta"},
        {"address": "14 Macquarie Street, Parramatta"},
    )
    assert passed, f"Expected address fuzzy match to pass: {failures}"

    # Missing critical token — should fail
    passed, failures = evaluator.evaluate_critical_tokens(
        {"customer_phone": "0423456789"},
        {},  # no slots captured
    )
    assert not passed, "Missing critical token should fail"
    assert any("not captured" in f for f in failures)


# ── Parametrised per-case live tests ─────────────────────────────────────────

@pytest.mark.eval
@pytest.mark.parametrize("case", _load_suite_b(), ids=lambda c: c.case_id)
def test_suite_b_case(case: EvalCase, runner: ReplayRunner):
    """Run a single Suite B case end-to-end and assert it passes."""
    trace = runner.run(case)
    evaluator = RuleBasedEvaluator()
    result = evaluator.evaluate(case, trace)

    collector = TraceCollector()
    enriched = collector.collect(trace)
    TraceCollector.save_trace(trace, TRACES_DIR)

    assert result.passed, (
        f"[{case.case_id}] FAILED\n"
        f"  Errors:   {result.errors}\n"
        f"  Intent:   got={trace.inferred_intent!r}  want={case.ground_truth.intent!r}\n"
        f"  Slots:    {trace.extracted_slots}\n"
        f"  Tools:    {trace.tools_called}\n"
        f"  Re-asks:  {enriched.re_ask_count}"
    )


# ── Full suite report ─────────────────────────────────────────────────────────

@pytest.mark.eval
def test_suite_b_report(runner: ReplayRunner):
    """Run all 50 Suite B cases and print a categorised precision report."""
    cases = _load_suite_b()
    evaluator = RuleBasedEvaluator()
    collector = TraceCollector()
    results = []

    for case in cases:
        trace = runner.run(case)
        result = evaluator.evaluate(case, trace)
        enriched = collector.collect(trace)
        TraceCollector.save_trace(trace, TRACES_DIR)
        results.append(result)

    print_report(results, suite_name="Suite B — Critical Precision (tradies)")
    save_results(results, RESULTS_DIR / "suite_b_latest.json")

    baseline_path = RESULTS_DIR / "suite_b_baseline.json"
    if baseline_path.exists():
        compare_to_baseline(results, baseline_path)

    passed = sum(1 for r in results if r.passed)
    total = len(results)
    pass_rate = passed / total if total else 0

    assert pass_rate >= 0.60, (
        f"Suite B pass rate {pass_rate:.1%} below 60% floor "
        f"({passed}/{total} passed)"
    )


# ── Category slice tests ──────────────────────────────────────────────────────

@pytest.mark.eval
def test_suite_b_phone_precision(runner: ReplayRunner):
    """All phone capture cases — critical token gate must pass."""
    cases = _cases_by_tag("phone")
    evaluator = RuleBasedEvaluator()
    failures = []
    for case in cases:
        trace = runner.run(case)
        result = evaluator.evaluate(case, trace)
        if not result.passed:
            failures.append(f"  {case.case_id}: {result.errors}")
    assert not failures, "Phone precision failures:\n" + "\n".join(failures)


@pytest.mark.eval
def test_suite_b_email_precision(runner: ReplayRunner):
    """All email capture cases — critical token gate must pass."""
    cases = _cases_by_tag("email")
    evaluator = RuleBasedEvaluator()
    failures = []
    for case in cases:
        trace = runner.run(case)
        result = evaluator.evaluate(case, trace)
        if not result.passed:
            failures.append(f"  {case.case_id}: {result.errors}")
    assert not failures, "Email precision failures:\n" + "\n".join(failures)


@pytest.mark.eval
def test_suite_b_service_disambiguation(runner: ReplayRunner):
    """Service disambiguation cases — service ID must be correctly classified."""
    cases = _cases_by_tag("service_disambiguation")
    evaluator = RuleBasedEvaluator()
    failures = []
    for case in cases:
        trace = runner.run(case)
        result = evaluator.evaluate(case, trace)
        if not result.passed:
            failures.append(f"  {case.case_id}: {result.errors}")
    assert not failures, "Service disambiguation failures:\n" + "\n".join(failures)


@pytest.mark.eval
def test_suite_b_p0_escalation(runner: ReplayRunner):
    """P0 cases (gas leak) must never result in a standard booking."""
    cases = [c for c in _load_suite_b() if c.risk_tier == "P0"]
    evaluator = RuleBasedEvaluator()
    failures = []
    for case in cases:
        trace = runner.run(case)
        result = evaluator.evaluate(case, trace)
        # P0 must not book — booking_confirmed is a failure
        if trace.final_outcome == "booking_confirmed":
            failures.append(
                f"  {case.case_id}: P0 case resulted in booking_confirmed — "
                "agent failed to escalate"
            )
    assert not failures, "P0 escalation failures:\n" + "\n".join(failures)


@pytest.mark.eval
def test_suite_b_tricky_suburbs(runner: ReplayRunner):
    """Tricky AU suburb names (Woolloomooloo, Wahroonga, Woollahra) must be captured correctly."""
    cases = _cases_by_tag("asr_risk")
    evaluator = RuleBasedEvaluator()
    failures = []
    for case in cases:
        trace = runner.run(case)
        result = evaluator.evaluate(case, trace)
        if not result.passed:
            failures.append(f"  {case.case_id}: {result.errors}")
    assert not failures, "Tricky suburb failures:\n" + "\n".join(failures)
