"""
Pytest configuration for the evals suite.

Fixtures:
    runner      — ReplayRunner (skipped if ANTHROPIC_API_KEY not set)
    evaluator   — RuleBasedEvaluator (always available, no API key needed)
    suite_a_dir — Path to Suite A case files

Markers:
    eval        — marks a test that calls the live LLM (requires ANTHROPIC_API_KEY)
    unit        — marks a test that runs without any API calls
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Ensure backend root is on the Python path so `app.*` imports resolve
_BACKEND_ROOT = Path(__file__).parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

# Load .env from the backend root so ANTHROPIC_API_KEY and other vars are available
load_dotenv(_BACKEND_ROOT / ".env")

from evals.evaluators.rule_based import RuleBasedEvaluator  # noqa: E402
from evals.runner.replay import ReplayRunner  # noqa: E402

# ---------------------------------------------------------------------------
# pytest markers
# ---------------------------------------------------------------------------

def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "eval: marks tests that call the live LLM (deselect with -m 'not eval')",
    )
    config.addinivalue_line(
        "markers",
        "unit: marks tests that run without any API calls",
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def skills_base_path() -> Path:
    return _BACKEND_ROOT / "skills"


@pytest.fixture(scope="session")
def runner(skills_base_path: Path) -> ReplayRunner:
    """
    Shared ReplayRunner for the whole test session.
    Skipped automatically if ANTHROPIC_API_KEY is not set.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set — skipping live eval tests")
    return ReplayRunner(skills_base_path=str(skills_base_path), anthropic_api_key=api_key)


@pytest.fixture(scope="session")
def evaluator() -> RuleBasedEvaluator:
    return RuleBasedEvaluator()


@pytest.fixture(scope="session")
def suite_a_dir() -> Path:
    return Path(__file__).parent / "cases" / "suite_a_happy_path"
