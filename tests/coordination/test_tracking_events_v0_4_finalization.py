from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FINALIZER_PATH = ROOT / "scripts/coordination/tracking_events_v0_4_finalization.py"
spec = importlib.util.spec_from_file_location("tracking_events_v04_finalization", FINALIZER_PATH)
assert spec is not None and spec.loader is not None
finalizer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(finalizer)


def sample_execution() -> dict:
    return {
        "focused_tests": {"collected": 1, "passed": 1},
        "full_suite": {"collected": 1, "passed": 1},
        "check_report": {"total": 11, "passed": 11, "warnings": 0, "failed": 0},
        "check_report_full": {"total": 11, "passed": 11, "warnings": 0, "failed": 0},
    }


def test_finalization_make_targets_are_explicit() -> None:
    text = (ROOT / "Makefile").read_text(encoding="utf-8")
    for target in (
        "tracking-events-v0-4-finalize-status",
        "tracking-events-v0-4-finalize-preflight",
        "tracking-events-v0-4-finalize-prepare",
        "tracking-events-v0-4-finalization-check",
        "tracking-events-v0-4-postpublication-idempotency-check",
    ):
        assert f"{target}:" in text


def test_real_subject_commit_is_bound() -> None:
    assert finalizer.SUBJECT_COMMIT == "cb1887a0c29784dfbf2da628065c716bf96917e9"


def test_requirement_results_cover_all_39_targets() -> None:
    rows = finalizer.requirement_results(finalizer.contract())
    assert len(rows) == 39
    assert len({row["obligation_id"] for row in rows}) == 39
    assert all(row["result"] == "satisfied" for row in rows)


def test_finalization_idempotency_is_sandboxed() -> None:
    evidence = finalizer.build_idempotency(
        "2026-08-18T12:00:00+03:00",
        sample_execution(),
        finalizer.historical_v03(),
    )
    assert evidence["first_run"]["result"] == "APPLIED"
    assert evidence["repeat_run"]["result"] == "IDEMPOTENT_NOOP"
    assert evidence["semantic_state_equal_after_repeat"] is True
    assert evidence["live_worktree_repeated_apply"] is False
