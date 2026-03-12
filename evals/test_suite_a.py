"""
Suite A — Happy Path eval tests.

Runs all 13 cases through the live LLM (Claude).
Requires ANTHROPIC_API_KEY to be set; skipped otherwise.

Run with:
    pytest evals/test_suite_a.py -v -m eval
    pytest evals/test_suite_a.py -v -m eval --tb=short -s   # verbose output
"""
from __future__ import annotations

from pathlib import Path

import pytest

from evals.evaluators.rule_based import RuleBasedEvaluator
from evals.report import load_cases_from_dir, print_report, save_results, run_suite
from evals.runner.replay import ReplayRunner
from evals.schema.case import EvalCase, RiskTier

pytestmark = pytest.mark.eval

_RESULTS_DIR = Path(__file__).parent / "results"


# ---------------------------------------------------------------------------
# Parametrised per-case tests
# ---------------------------------------------------------------------------

def _all_suite_a_cases() -> list[EvalCase]:
    cases_dir = Path(__file__).parent / "cases" / "suite_a_happy_path"
    return load_cases_from_dir(cases_dir)


@pytest.mark.parametrize("case", _all_suite_a_cases(), ids=lambda c: c.case_id)
def test_suite_a_case(case: EvalCase, runner: ReplayRunner, evaluator: RuleBasedEvaluator):
    """
    Each case must pass all active hard gates.

    P1 failures are surfaced with a clear assertion message so they
    appear immediately in CI output without needing --tb=long.
    """
    trace = runner.run(case)

    assert trace.error is None, (
        f"[{case.case_id}] Runner error: {trace.error}"
    )

    result = evaluator.evaluate(case, trace)

    # Always assert for P0/P1 — these are hard operational failures
    if case.risk_tier in (RiskTier.P0, RiskTier.P1):
        assert result.passed, (
            f"[{case.risk_tier}] {case.case_id} FAILED\n"
            f"  Errors: {result.errors}\n"
            f"  Intent:  {result.intent_score.score:.1f}/3  "
            f"Slots: {result.slot_score.score:.1f}/3  "
            f"Tools: {result.tool_score.score:.1f}/3  "
            f"Outcome: {result.outcome_score.score:.1f}/3"
        )
    else:
        # P2/P3 — warn but don't fail CI; score must be non-zero
        if not result.passed:
            pytest.warns(
                UserWarning,
                match=f"{case.case_id}",
            ) if False else None  # non-blocking: just print
            print(f"\n  [P{case.risk_tier}] {case.case_id} soft-fail: {result.errors}")

        assert result.composite_score > 0.0, (
            f"[{case.case_id}] Composite score is 0 — agent produced no useful output"
        )


# ---------------------------------------------------------------------------
# Full suite run with report (single test that runs all and prints summary)
# ---------------------------------------------------------------------------

def test_suite_a_report(runner: ReplayRunner, evaluator: RuleBasedEvaluator, suite_a_dir: Path):
    """
    Run all Suite A cases and print a structured report.
    Saves results to evals/results/suite_a_latest.json for baseline comparison.
    """
    results = run_suite(suite_a_dir, runner, evaluator, verbose=True)

    print_report(results, suite_name="Suite A — Happy Path")

    # Save results for regression tracking
    save_results(results, _RESULTS_DIR / "suite_a_latest.json")

    # Aggregate gate: P1+ pass rate must be >= 80%
    p1_results = [r for r in results if r.risk_tier in (RiskTier.P0, RiskTier.P1)]
    if p1_results:
        p1_pass_rate = sum(1 for r in p1_results if r.passed) / len(p1_results)
        assert p1_pass_rate >= 0.80, (
            f"P1 pass rate {p1_pass_rate:.0%} is below the 80% threshold. "
            f"Failed P1 cases: {[r.case_id for r in p1_results if not r.passed]}"
        )

    # Composite average must be above 1.5/3.0
    composite_avg = sum(r.composite_score for r in results) / len(results)
    assert composite_avg >= 1.5, (
        f"Overall composite score {composite_avg:.2f} is below minimum threshold of 1.5"
    )
