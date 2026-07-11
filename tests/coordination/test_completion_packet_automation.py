from pathlib import Path

import yaml

from scripts.coordination.apply_completion_packet import (
    apply_completion_packet,
)
from scripts.coordination.validate_completion_packet import (
    validate_packet,
)


def build_packet() -> dict[str, object]:
    return {
        "completion_id": "logistics_bootstrap_completed",
        "module_id": "logistics_service",
        "module_name": "ForPrint Logistics Service",
        "phase": "bootstrap_and_coordination_foundation_v0_1",
        "prompt_id": ("logistics_service_bootstrap_and_coordination_foundation_v0_1"),
        "report_id": "2026-07-11-logistics-service-bootstrap-completion",
        "report_path": (
            "coordination/reports/completion/logistics_service_bootstrap_completion.md"
        ),
        "created_at": "2026-07-11T20:00:00+03:00",
        "branch": "feature/logistics-bootstrap-coordination-v01",
        "implementation_commit": "abc1234",
        "push_status": "not_pushed",
        "summary": "Bootstrap completed.",
        "implemented": ["Provider-neutral domain foundation."],
        "checks": {
            "check_report": "ok",
            "tests": "ok",
            "governance_check": "ok",
        },
        "instruction_sources_reviewed": [
            "Blueprint logistics module guide.",
        ],
        "standards_reviewed": [
            "Module prompt completion protocol.",
        ],
        "standards_alignment_notes": [
            "No destructive rewrite was performed.",
        ],
        "boundary_confirmation": {
            "production_api_added": False,
            "live_external_integrations_added": False,
            "database_ownership_added": False,
            "operational_data_ownership_added": False,
            "queue_or_cache_dependency_added": False,
            "one_c_writes_added": False,
            "automatic_posting_added": False,
            "final_price_calculation_added": False,
            "live_provider_writes_added": False,
            "real_provider_credentials_committed": False,
            "blueprint_repository_written_directly": False,
        },
        "current_outputs": ["app/domain/"],
        "next_recommended_steps": ["Await Blueprint review."],
        "next_questions_for_blueprint": [],
    }


def prepare_project_root(root: Path) -> None:
    paths = (
        root / "coordination/status",
        root / "coordination/prompts",
        root / "coordination/reports/completion",
    )

    for path in paths:
        path.mkdir(parents=True, exist_ok=True)

    status = {
        "module_id": "logistics_service",
        "module_status": "active",
        "priority": "p0",
        "current_phase": "bootstrap",
        "last_completed_step": "none",
        "last_updated": "2026-07-11",
        "branch": "feature/test",
        "last_commit": "abc0000",
        "checks": {},
        "boundary": {},
        "recommended_next_step": "continue",
    }

    prompts = {
        "module_id": "logistics_service",
        "prompts": [
            {
                "prompt_id": ("logistics_service_bootstrap_and_coordination_foundation_v0_1"),
                "file": "coordination/prompts/received/prompt.md",
                "status": "active",
            }
        ],
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


def test_completion_packet_validator_accepts_safe_packet() -> None:
    assert validate_packet(build_packet()) == []


def test_completion_packet_validator_rejects_live_write() -> None:
    packet = build_packet()
    packet["boundary_confirmation"]["live_provider_writes_added"] = True

    errors = validate_packet(packet)

    assert any("live_provider_writes_added" in error for error in errors)


def test_completion_packet_apply_is_idempotent(tmp_path: Path) -> None:
    prepare_project_root(tmp_path)

    packet_path = tmp_path / "packet.yaml"
    packet_path.write_text(
        yaml.safe_dump(build_packet(), sort_keys=False),
        encoding="utf-8",
    )

    first_changed = apply_completion_packet(packet_path, tmp_path)

    tracked_paths = (
        "coordination/status/current_status.yaml",
        "coordination/status/current_status.md",
        "coordination/status/next_questions_for_blueprint.md",
        "coordination/prompts/index.yaml",
        "coordination/reports/index.yaml",
        "coordination/reports/completion/logistics_service_bootstrap_completion.md",
    )

    first_snapshot = {path: (tmp_path / path).read_text(encoding="utf-8") for path in tracked_paths}

    second_changed = apply_completion_packet(packet_path, tmp_path)

    second_snapshot = {
        path: (tmp_path / path).read_text(encoding="utf-8") for path in tracked_paths
    }

    assert first_changed
    assert second_changed == []
    assert first_snapshot == second_snapshot
