from pathlib import Path

from scripts.validation.check_project_policies import (
    run_policy_checks,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_project_policy_checker_passes_current_repository() -> None:
    results = run_policy_checks(PROJECT_ROOT)
    failed = [result for result in results if result.status == "FAILED"]

    assert failed == [], [f"{result.name}: {result.details}" for result in failed]
