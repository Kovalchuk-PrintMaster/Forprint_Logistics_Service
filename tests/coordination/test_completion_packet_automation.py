from __future__ import annotations

from pathlib import Path

import yaml

from scripts.coordination.apply_completion_packet import (
    apply_completion_packet,
)
from scripts.coordination.validate_completion_packet import (
    CURRENT_INTAKE_PROTOCOL,
    CURRENT_PACKET_SCHEMA,
    validate_packet,
)


def build_packet() -> dict[str, object]:
    return {
        "schema_version": CURRENT_PACKET_SCHEMA,
        "protocol_version": CURRENT_INTAKE_PROTOCOL,
        "completion_id": "logistics_bootstrap_completed_v0_2",
        "module_id": "logistics_service",
        "module_name": "ForPrint Logistics Service",
        "phase": "bootstrap_and_coordination_foundation_v0_1",
        "prompt_id": ("logistics_service_bootstrap_and_coordination_foundation_v0_1"),
        "report_id": "logistics_bootstrap_completion_v0_2",
        "report_path": (
            "coordination/reports/completion/logistics_service_bootstrap_completion_v0_2.md"
        ),
        "created_at": "2026-08-07T16:30:00+03:00",
        "branch": "feature/logistics-bootstrap-coordination-v01",
        "implementation_commit": "a" * 40,
        "push_status": "pushed",
        "summary": "Bootstrap completion evidence refreshed.",
        "implemented": ["Provider-neutral domain foundation."],
        "checks": {
            "check_report": "ok",
            "tests": "ok",
            "governance_check": "ok",
            "check_report_failed": 0,
            "check_report_warnings": 0,
        },
        "instruction_sources_reviewed": [
            "Blueprint logistics module guide.",
        ],
        "standards_reviewed": [
            "Completion intake governance v0.2.",
        ],
        "standards_alignment_notes": [
            "Historical completion artifacts were not rewritten.",
        ],
        "boundary_confirmation": {
            "no_production_api": True,
            "no_live_external_integrations": True,
            "no_real_1c_sync": True,
            "no_production_write": True,
            "no_automatic_posting": True,
        },
        "current_outputs": ["app/domain/"],
        "next_recommended_steps": ["Await Blueprint intake."],
        "next_questions_for_blueprint": [],
        "blockers": [],
        "dependency_implications": [],
        "completion_evidence_complete": True,
    }


def prepare_project_root(root: Path) -> None:
    for path in (
        root / "coordination/status",
        root / "coordination/prompts",
        root / "coordination/reports/completion",
    ):
        path.mkdir(parents=True, exist_ok=True)

    status = {
        "module_id": "logistics_service",
        "module_status": "active",
        "boundaries": {},
        "progress_summary": {},
    }

    prompts = {
        "module_id": "logistics_service",
        "prompts": [
            {
                "prompt_id": ("logistics_service_bootstrap_and_coordination_foundation_v0_1"),
                "file": "coordination/prompts/received/prompt.md",
                "status": "completed_in_module",
                "blueprint_review_status": "not_started",
            }
        ],
        "active_prompt_id": None,
    }

    reports = {
        "module_id": "logistics_service",
        "reports": [],
    }

    (root / "coordination/status/current_status.yaml").write_text(
        yaml.safe_dump(status, sort_keys=False),
        encoding="utf-8",
    )
    (root / "coordination/status/current_status.md").write_text(
        "# Status\n",
        encoding="utf-8",
    )
    (root / "coordination/status/next_questions_for_blueprint.md").write_text(
        "# Questions\n",
        encoding="utf-8",
    )
    (root / "coordination/prompts/index.yaml").write_text(
        yaml.safe_dump(prompts, sort_keys=False),
        encoding="utf-8",
    )
    (root / "coordination/reports/index.yaml").write_text(
        yaml.safe_dump(reports, sort_keys=False),
        encoding="utf-8",
    )


def test_current_packet_validator_accepts_v0_2_packet() -> None:
    assert validate_packet(build_packet()) == []


def test_current_packet_rejects_missing_schema() -> None:
    packet = build_packet()
    packet.pop("schema_version")

    errors = validate_packet(packet)

    assert "Missing required field: schema_version" in errors


def test_current_packet_rejects_wrong_protocol() -> None:
    packet = build_packet()
    packet["protocol_version"] = "wrong"

    errors = validate_packet(packet)

    assert any("protocol_version" in error for error in errors)


def test_current_packet_requires_full_git_sha() -> None:
    packet = build_packet()
    packet["implementation_commit"] = "abcdef1"

    errors = validate_packet(packet)

    assert any("40-character" in error for error in errors)


def test_current_packet_requires_positive_safety_confirmation() -> None:
    packet = build_packet()
    packet["boundary_confirmation"]["no_production_write"] = False

    errors = validate_packet(packet)

    assert any("no_production_write" in error for error in errors)


def test_current_packet_rejects_string_safety_confirmation() -> None:
    packet = build_packet()
    packet["boundary_confirmation"]["no_production_write"] = "true"

    errors = validate_packet(packet)

    assert any("no_production_write" in error for error in errors)


def test_superseding_packet_requires_revision_reason() -> None:
    packet = build_packet()
    packet["supersedes_completion_id"] = "old_completion"

    errors = validate_packet(packet)

    assert any("provided together" in error for error in errors)


def test_superseding_packet_pair_is_valid() -> None:
    packet = build_packet()
    packet["supersedes_completion_id"] = "old_completion"
    packet["revision_reason"] = "Protocol compatibility correction."

    assert validate_packet(packet) == []


def test_blockers_are_machine_readable_list() -> None:
    packet = build_packet()
    packet["blockers"] = ["WAITING_FOR_EXTERNAL_REVIEW"]

    assert validate_packet(packet) == []

    packet["blockers"] = "WAITING_FOR_EXTERNAL_REVIEW"
    errors = validate_packet(packet)

    assert any("blockers must be a list" in error for error in errors)


def test_completion_packet_apply_is_idempotent(
    tmp_path: Path,
) -> None:
    prepare_project_root(tmp_path)

    packet_path = tmp_path / "packet.yaml"
    packet_path.write_text(
        yaml.safe_dump(build_packet(), sort_keys=False),
        encoding="utf-8",
    )

    first_changed = apply_completion_packet(
        packet_path,
        tmp_path,
    )

    assert first_changed

    tracked_paths = (
        "coordination/status/current_status.yaml",
        "coordination/status/current_status.md",
        "coordination/status/next_questions_for_blueprint.md",
        "coordination/prompts/index.yaml",
        "coordination/reports/index.yaml",
        ("coordination/reports/completion/logistics_service_bootstrap_completion_v0_2.md"),
    )

    first_snapshot = {path: (tmp_path / path).read_text(encoding="utf-8") for path in tracked_paths}

    second_changed = apply_completion_packet(
        packet_path,
        tmp_path,
    )

    second_snapshot = {
        path: (tmp_path / path).read_text(encoding="utf-8") for path in tracked_paths
    }

    assert second_changed == []
    assert first_snapshot == second_snapshot

    prompt_index = yaml.safe_load(
        (tmp_path / "coordination/prompts/index.yaml").read_text(encoding="utf-8")
    )
    prompt = prompt_index["prompts"][0]

    assert prompt["implementation_commit"] == "a" * 40
    assert prompt["completion_commit"] is None
    assert prompt["completion_schema_version"] == CURRENT_PACKET_SCHEMA
