from __future__ import annotations

from pathlib import Path

import yaml

from scripts.coordination.apply_completion_packet import (
    apply_completion_packet,
)


def write_yaml(
    path: Path,
    data: dict[str, object],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            data,
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )


def build_packet() -> dict[str, object]:
    return {
        "schema_version": "module_completion_packet_v0_2",
        "protocol_version": "blueprint_completion_intake_v0_2",
        "completion_id": ("logistics_service_boundary_and_local_model_v0_1_completed_v0_2"),
        "module_id": "logistics_service",
        "module_name": "ForPrint Logistics Service",
        "phase": "boundary_and_local_model_v0_1",
        "prompt_id": ("logistics_service_boundary_and_local_model_v0_1"),
        "report_id": ("logistics_service_boundary_and_local_model_v0_1_completion_v0_2"),
        "report_path": (
            "coordination/reports/completion/"
            "logistics_service_boundary_and_local_model_v0_1_"
            "completion_v0_2.md"
        ),
        "created_at": "2026-08-07T16:30:00+03:00",
        "branch": "feature/logistics-boundary-local-model-v01",
        "implementation_commit": "b" * 40,
        "push_status": "pushed",
        "summary": "Completed local model.",
        "implemented": ["Added local model."],
        "checks": {
            "check_report": "ok",
            "tests": "ok",
            "governance_check": "ok",
        },
        "instruction_sources_reviewed": ["Active prompt."],
        "standards_reviewed": ["Completion protocol v0.2."],
        "standards_alignment_notes": ["Module-only writes."],
        "boundary_confirmation": {
            "no_production_api": True,
            "no_live_external_integrations": True,
            "no_real_1c_sync": True,
            "no_production_write": True,
            "no_automatic_posting": True,
        },
        "current_outputs": ["app/domain/"],
        "next_recommended_steps": ["Wait for Blueprint review."],
        "next_questions_for_blueprint": [],
        "blockers": [],
        "dependency_implications": [],
        "completion_evidence_complete": True,
    }


def prepare_project(root: Path) -> Path:
    active_relative = Path(
        "coordination/prompts/active/"
        "2026-07-11__logistics_service__"
        "boundary_and_local_model_v0_1.md"
    )
    active_path = root / active_relative
    active_path.parent.mkdir(parents=True, exist_ok=True)
    active_path.write_text(
        "# Active prompt\n",
        encoding="utf-8",
    )

    write_yaml(
        root / "coordination/prompts/index.yaml",
        {
            "schema_version": "module_prompt_index_v0_1",
            "module_id": "logistics_service",
            "prompts": [
                {
                    "prompt_id": ("logistics_service_boundary_and_local_model_v0_1"),
                    "status": "active",
                    "module_execution_status": "ready_for_module_pull",
                    "blueprint_review_status": "not_started",
                    "active_file": str(active_relative),
                    "completion_report": None,
                    "completion_commit": None,
                }
            ],
            "active_prompt_id": ("logistics_service_boundary_and_local_model_v0_1"),
        },
    )

    write_yaml(
        root / "coordination/reports/index.yaml",
        {
            "schema_version": "module_report_index_v0_1",
            "module_id": "logistics_service",
            "reports": [],
        },
    )

    write_yaml(
        root / "coordination/status/current_status.yaml",
        {
            "schema_version": "module_status_v0_1",
            "module_id": "logistics_service",
            "module_name": "ForPrint Logistics Service",
            "boundaries": {},
            "progress_summary": {},
            "prompt_progress": {
                "intake": "completed",
                "implementation": "not_started",
                "tests": "not_run",
                "completion": "not_started",
            },
        },
    )

    packet_path = root / "coordination/completion_packets/records/completion.yaml"
    write_yaml(packet_path, build_packet())

    return packet_path


def test_completion_closes_local_prompt_lifecycle(
    tmp_path: Path,
) -> None:
    packet_path = prepare_project(tmp_path)

    changed = apply_completion_packet(
        packet_path,
        tmp_path,
    )

    assert changed

    prompt_index = yaml.safe_load(
        (tmp_path / "coordination/prompts/index.yaml").read_text(encoding="utf-8")
    )
    prompt = prompt_index["prompts"][0]

    assert prompt["status"] == "completed_in_module"
    assert prompt["module_execution_status"] == "completed_by_module"
    assert prompt["blueprint_review_status"] == "not_started"
    assert prompt["completion_commit"] is None
    assert "active_file" not in prompt
    assert prompt["archived_file"].startswith("coordination/prompts/archived/")
    assert prompt_index["active_prompt_id"] is None

    archived_path = tmp_path / prompt["archived_file"]

    assert archived_path.is_file()
    assert not any((tmp_path / "coordination/prompts/active").glob("*.md"))

    status = yaml.safe_load(
        (tmp_path / "coordination/status/current_status.yaml").read_text(encoding="utf-8")
    )

    assert status["status"] == ("completed_in_module")
    assert status["completion_commit"] is None
    assert status["automatic_acceptance"] is False
    assert status["completion_protocol"] == {
        "schema_version": "module_completion_packet_v0_2",
        "protocol_version": "blueprint_completion_intake_v0_2",
        "supersedes_completion_id": None,
        "revision_reason": None,
    }

    second_changed = apply_completion_packet(
        packet_path,
        tmp_path,
    )

    assert second_changed == []


def test_historical_packet_is_not_rewritten(
    tmp_path: Path,
) -> None:
    packet_path = prepare_project(tmp_path)

    historical = tmp_path / "coordination/completion_packets/records/historical_v0_1.yaml"
    historical.parent.mkdir(parents=True, exist_ok=True)
    historical.write_text(
        ("completion_id: historical\nboundary_confirmation:\n  production_api_added: false\n"),
        encoding="utf-8",
    )
    before = historical.read_bytes()

    apply_completion_packet(
        packet_path,
        tmp_path,
    )

    assert historical.read_bytes() == before
