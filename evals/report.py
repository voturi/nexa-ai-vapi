"""
Eval report — metrics aggregation and baseline comparison.

Usage:
    from evals.report import run_suite, print_report, save_results
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from evals.evaluators.rule_based import RuleBasedEvaluator
from evals.runner.replay import ReplayRunner
from evals.schema.case import EvalCase, EvalResult, RiskTier


# ---------------------------------------------------------------------------
# Case loading
# ---------------------------------------------------------------------------

def load_cases_from_dir(cases_dir: Path) -> list[EvalCase]:
    """Load all JSON test cases from a directory, sorted by case_id."""
    cases = []
    for json_file in sorted(cases_dir.glob("*.json")):
        try:
            cases.append(EvalCase.from_file(json_file))
        except Exception as exc:
            print(f"  [WARN] Could not load {json_file.name}: {exc}")
    return cases


# ---------------------------------------------------------------------------
# Suite runner
# ---------------------------------------------------------------------------

def run_suite(
    cases_dir: Path,
    runner: ReplayRunner,
    evaluator: RuleBasedEvaluator,
    *,
    verbose: bool = False,
) -> list[EvalResult]:
    """Run all cases in a directory. Returns one EvalResult per case."""
    cases = load_cases_from_dir(cases_dir)
    results: list[EvalResult] = []

    for case in cases:
        if verbose:
            print(f"  Running {case.case_id} ...", end=" ", flush=True)

        trace = runner.run(case)
        result = evaluator.evaluate(case, trace)
        results.append(result)

        if verbose:
            status = "PASS" if result.passed else "FAIL"
            print(f"{status}  (composite: {result.composite_score:.2f})")

    return results


# ---------------------------------------------------------------------------
# Report printing
# ---------------------------------------------------------------------------

def print_report(results: list[EvalResult], suite_name: str = "Eval Suite") -> None:
    """Print a structured report to stdout."""
    total = len(results)
    if total == 0:
        print(f"\n{suite_name}: No results to report.")
        return

    passed = sum(1 for r in results if r.passed)
    failed = total - passed

    # Dimension averages
    intent_avg = sum(r.intent_score.score for r in results) / total
    slot_avg = sum(r.slot_score.score for r in results) / total
    tool_avg = sum(r.tool_score.score for r in results) / total
    outcome_avg = sum(r.outcome_score.score for r in results) / total
    composite_avg = sum(r.composite_score for r in results) / total

    # Slices
    by_tier: dict[str, list[EvalResult]] = defaultdict(list)
    by_domain: dict[str, list[EvalResult]] = defaultdict(list)
    by_scenario: dict[str, list[EvalResult]] = defaultdict(list)

    for r in results:
        by_tier[r.risk_tier].append(r)
        by_domain[r.business_domain].append(r)
        by_scenario[r.scenario_type].append(r)

    # ── Print ──────────────────────────────────────────────────────────────
    w = 60
    print(f"\n{'═' * w}")
    print(f"  {suite_name}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'═' * w}")

    print(f"\n  Overall")
    print(f"    Cases:      {total}")
    print(f"    Passed:     {passed}  ({passed / total * 100:.1f}%)")
    print(f"    Failed:     {failed}  ({failed / total * 100:.1f}%)")

    print(f"\n  Dimension Scores  (0 – 3)")
    print(f"    Intent accuracy   {intent_avg:.2f}")
    print(f"    Slot accuracy     {slot_avg:.2f}")
    print(f"    Tool accuracy     {tool_avg:.2f}")
    print(f"    Outcome accuracy  {outcome_avg:.2f}")
    print(f"    ─────────────────────")
    print(f"    Composite avg     {composite_avg:.2f}")

    print(f"\n  By Risk Tier")
    for tier in [RiskTier.P0, RiskTier.P1, RiskTier.P2, RiskTier.P3]:
        tr = by_tier.get(tier, [])
        if tr:
            tp = sum(1 for r in tr if r.passed)
            print(f"    {tier}  {tp}/{len(tr)} passed")

    print(f"\n  By Domain")
    for domain, dr in sorted(by_domain.items()):
        dp = sum(1 for r in dr if r.passed)
        print(f"    {domain:<20} {dp}/{len(dr)} passed")

    print(f"\n  By Scenario")
    for scenario, sr in sorted(by_scenario.items()):
        sp = sum(1 for r in sr if r.passed)
        print(f"    {scenario:<30} {sp}/{len(sr)} passed")

    # Failed case details
    failed_results = [r for r in results if not r.passed]
    if failed_results:
        print(f"\n  Failed Cases")
        for r in failed_results:
            print(f"    [{r.risk_tier}] {r.case_id}")
            for err in r.errors:
                print(f"           → {err}")

    print(f"\n{'═' * w}\n")


# ---------------------------------------------------------------------------
# Baseline save / compare
# ---------------------------------------------------------------------------

def save_results(results: list[EvalResult], output_path: Path) -> None:
    """Persist results as JSON for baseline comparison across runs."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now().isoformat(),
        "total": len(results),
        "passed": sum(1 for r in results if r.passed),
        "composite_avg": round(sum(r.composite_score for r in results) / len(results), 3) if results else 0,
        "results": [r.model_dump() for r in results],
    }
    with open(output_path, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    print(f"  Results saved → {output_path}")


def compare_to_baseline(
    current: list[EvalResult],
    baseline_path: Path,
) -> None:
    """Print a regression delta between current results and a saved baseline."""
    if not baseline_path.exists():
        print(f"  No baseline found at {baseline_path}. Run save_results() first.")
        return

    with open(baseline_path) as f:
        baseline_data = json.load(f)

    baseline_by_id = {r["case_id"]: r for r in baseline_data["results"]}
    current_by_id = {r.case_id: r for r in current}

    regressions = []
    improvements = []

    for case_id, cur in current_by_id.items():
        base = baseline_by_id.get(case_id)
        if not base:
            continue
        if cur.passed and not base["passed"]:
            improvements.append(case_id)
        elif not cur.passed and base["passed"]:
            regressions.append(case_id)

    print(f"\n  Regression Delta vs {baseline_path.name}")
    print(f"    Regressions (was PASS, now FAIL):  {len(regressions)}")
    for case_id in regressions:
        print(f"      ✗ {case_id}")
    print(f"    Improvements (was FAIL, now PASS): {len(improvements)}")
    for case_id in improvements:
        print(f"      ✓ {case_id}")
