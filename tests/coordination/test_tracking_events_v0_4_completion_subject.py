from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = ROOT / "scripts/coordination/tracking_events_v0_4_completion_subject.py"

spec = importlib.util.spec_from_file_location(
    "tracking_events_v04_completion_subject",
    WORKFLOW_PATH,
)
assert spec is not None
assert spec.loader is not None
workflow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow)


def test_subject_targets_are_explicit_make_commands() -> None:
    text = (ROOT / "Makefile").read_text(encoding="utf-8")
    for target in (
        "tracking-events-v0-4-subject-status",
        "tracking-events-v0-4-subject-preflight",
        "tracking-events-v0-4-subject-prepare",
        "tracking-events-v0-4-subject-check",
        "tracking-events-v0-4-finalization-idempotency-check",
    ):
        assert f"{target}:" in text


def test_finalization_idempotency_uses_real_commit_shape() -> None:
    evidence = workflow.build_idempotency("2026-08-18T12:00:00+03:00")
    assert evidence["first_run"]["result"] == "APPLIED"
    assert evidence["repeat_run"]["result"] == "IDEMPOTENT_NOOP"
    assert evidence["semantic_state_equal_after_repeat"] is True
    assert evidence["live_worktree_mutated"] is False


def test_prepublication_subject_does_not_create_packet_or_outbox() -> None:
    subject = workflow.build_subject_manifest(
        "2026-08-18T12:00:00+03:00",
        {
            "focused_tests": {"collected": 1, "passed": 1},
            "full_suite": {"collected": 1, "passed": 1},
            "check_report": {
                "total": 11,
                "passed": 11,
                "warnings": 0,
                "failed": 0,
            },
            "check_report_full": {
                "total": 11,
                "passed": 11,
                "warnings": 0,
                "failed": 0,
            },
        },
    )
    assert subject["prepublication_target_obligations_satisfied"] == 38
    assert subject["pending_completion_evidence_obligation"] == "CE-009"
    assert subject["completion_packet_created"] is False
    assert subject["completion_outbox_created"] is False
    assert subject["live_v0_4_terminal_coordination_applied"] is False


def test_live_coordination_is_not_mutated_by_prepare_source() -> None:
    source = WORKFLOW_PATH.read_text(encoding="utf-8")
    prepare = source.split("def prepare() -> None:", 1)[1].split(
        "def subject_check() -> None:",
        1,
    )[0]
    assert "apply_finalized_coordination(ROOT" not in prepare


def test_packet_creation_is_deferred_until_ce009_exists() -> None:
    source = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "packet_creation_allowed_now=false" in source
    assert "pending_obligation=CE-009" in source
