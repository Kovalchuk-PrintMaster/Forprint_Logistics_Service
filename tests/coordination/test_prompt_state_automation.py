from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from scripts.coordination.sync_prompt_state import (
    sync_prompt_state,
    validate_prompt_state,
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
        ),
        encoding="utf-8",
    )


def prepare_project(root: Path) -> dict[str, Path]:
    blueprint_module = root / "blueprint/logistics_service"
    approved = blueprint_module / "approved"

    approved.mkdir(parents=True)

    bootstrap_name = "2026-07-09__logistics_service__bootstrap_and_coordination_foundation_v0_1.md"
    active_name = "2026-07-11__logistics_service__boundary_and_local_model_v0_1.md"

    (approved / bootstrap_name).write_text(
        "# Bootstrap prompt\n",
        encoding="utf-8",
    )
    (approved / active_name).write_text(
        "# Active prompt\n",
        encoding="utf-8",
    )

    blueprint_index = root / "blueprint/index.yaml"

    write_yaml(
        blueprint_index,
        {
            "schema_version": "prompt_queue_v0_2",
            "module": "logistics_service",
            "prompt_queue": [
                {
                    "prompt_id": ("logistics_service_bootstrap_and_coordination_foundation_v0_1"),
                    "sequence": 1,
                    "title": "Bootstrap",
                    "file": f"approved/{bootstrap_name}",
                    "target_module": "logistics_service",
                    "phase": ("bootstrap_and_coordination_foundation_v0_1"),
                    "priority": "high",
                    "module_execution": {
                        "status": "completed_by_module",
                        "completion_commit": "abc1234",
                        "completion_report": ("coordination/reports/completion/bootstrap.md"),
                    },
                    "blueprint_review": {
                        "status": "accepted_by_blueprint",
                        "acceptance_commit": "def5678",
                        "accepted_at": "2026-07-11",
                    },
                },
                {
                    "prompt_id": ("logistics_service_boundary_and_local_model_v0_1"),
                    "sequence": 2,
                    "title": ("Boundary and Local Model Foundation"),
                    "file": f"approved/{active_name}",
                    "target_module": "logistics_service",
                    "phase": ("boundary_and_local_model_v0_1"),
                    "priority": "high",
                    "module_execution": {
                        "status": "ready_for_module_pull",
                        "completion_commit": None,
                        "completion_report": None,
                    },
                    "blueprint_review": {
                        "status": "not_started",
                        "acceptance_commit": None,
                        "accepted_at": None,
                    },
                },
            ],
        },
    )

    local_index = root / "coordination/prompts/index.yaml"

    write_yaml(
        local_index,
        {
            "schema_version": ("module_prompt_index_v0_1"),
            "module_id": "logistics_service",
            "prompts": [
                {
                    "prompt_id": ("logistics_service_bootstrap_and_coordination_foundation_v0_1"),
                    "status": "completed_in_module",
                    "completion_commit": "implementation1",
                    "completion_report": ("coordination/reports/completion/bootstrap.md"),
                }
            ],
        },
    )

    status = root / "coordination/status/current_status.yaml"

    write_yaml(
        status,
        {
            "schema_version": "module_status_v0_1",
            "module_id": "logistics_service",
            "module_name": ("ForPrint Logistics Service"),
            "module_status": "active",
            "priority": "p0",
            "current_phase": "bootstrap",
            "last_completed_step": "bootstrap_completed",
            "last_updated": "2026-07-11",
            "branch": "feature/bootstrap",
            "last_commit": "abc1234",
            "checks": {},
            "boundary": {},
            "recommended_next_step": "wait",
            "status": "completed_in_module",
            "phase": "bootstrap",
            "source_prompt_id": "bootstrap",
            "updated_at": ("2026-07-11T20:00:00+03:00"),
            "implementation_commit": "abc1234",
            "push_status": "pushed",
            "progress_summary": {},
            "current_step": {},
            "open_questions": [],
        },
    )

    return {
        "blueprint_module": blueprint_module,
        "blueprint_index": blueprint_index,
        "received": (root / "coordination/prompts/received"),
        "active": (root / "coordination/prompts/active"),
        "archived": (root / "coordination/prompts/archived"),
        "local_index": local_index,
        "status": status,
        "status_md": (root / "coordination/status/current_status.md"),
        "questions": (root / "coordination/status/next_questions_for_blueprint.md"),
    }


def snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): (path.read_bytes())
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_sync_activates_next_prompt_and_is_idempotent(
    tmp_path: Path,
) -> None:
    paths = prepare_project(tmp_path)
    now = datetime(
        2026,
        7,
        12,
        12,
        0,
        tzinfo=ZoneInfo("Europe/Kyiv"),
    )

    first = sync_prompt_state(
        module_id="logistics_service",
        blueprint_index_path=(paths["blueprint_index"]),
        blueprint_module_dir=(paths["blueprint_module"]),
        received_dir=paths["received"],
        active_dir=paths["active"],
        archived_dir=paths["archived"],
        local_index_path=paths["local_index"],
        status_yaml_path=paths["status"],
        status_markdown_path=paths["status_md"],
        questions_path=paths["questions"],
        branch="feature/local-model",
        commit="abcd1234",
        now=now,
    )

    assert first.active_prompt_id == ("logistics_service_boundary_and_local_model_v0_1")
    assert len(list(paths["received"].glob("*.md"))) == 2
    assert len(list(paths["active"].glob("*.md"))) == 1
    assert len(list(paths["archived"].glob("*.md"))) == 1

    local_index = yaml.safe_load(paths["local_index"].read_text(encoding="utf-8"))

    active_entries = [prompt for prompt in local_index["prompts"] if prompt["status"] == "active"]

    assert len(active_entries) == 1
    assert active_entries[0]["prompt_id"] == ("logistics_service_boundary_and_local_model_v0_1")

    status = yaml.safe_load(paths["status"].read_text(encoding="utf-8"))

    assert status["source_prompt_id"] == ("logistics_service_boundary_and_local_model_v0_1")
    assert status["status"] == "prompt_active"

    assert (
        validate_prompt_state(
            local_index_path=paths["local_index"],
            status_yaml_path=paths["status"],
            received_dir=paths["received"],
            active_dir=paths["active"],
        )
        == []
    )

    first_snapshot = snapshot(tmp_path)

    sync_prompt_state(
        module_id="logistics_service",
        blueprint_index_path=(paths["blueprint_index"]),
        blueprint_module_dir=(paths["blueprint_module"]),
        received_dir=paths["received"],
        active_dir=paths["active"],
        archived_dir=paths["archived"],
        local_index_path=paths["local_index"],
        status_yaml_path=paths["status"],
        status_markdown_path=paths["status_md"],
        questions_path=paths["questions"],
        branch="feature/local-model",
        commit="abcd1234",
        now=now,
    )

    assert snapshot(tmp_path) == first_snapshot


def test_prompt_state_check_rejects_multiple_active_files(
    tmp_path: Path,
) -> None:
    paths = prepare_project(tmp_path)

    sync_prompt_state(
        module_id="logistics_service",
        blueprint_index_path=(paths["blueprint_index"]),
        blueprint_module_dir=(paths["blueprint_module"]),
        received_dir=paths["received"],
        active_dir=paths["active"],
        archived_dir=paths["archived"],
        local_index_path=paths["local_index"],
        status_yaml_path=paths["status"],
        status_markdown_path=paths["status_md"],
        questions_path=paths["questions"],
        branch="feature/local-model",
        commit="abcd1234",
        now=datetime(
            2026,
            7,
            12,
            12,
            0,
            tzinfo=ZoneInfo("Europe/Kyiv"),
        ),
    )

    (paths["active"] / "unexpected.md").write_text(
        "# Unexpected\n",
        encoding="utf-8",
    )

    errors = validate_prompt_state(
        local_index_path=paths["local_index"],
        status_yaml_path=paths["status"],
        received_dir=paths["received"],
        active_dir=paths["active"],
    )

    assert any("exactly one Markdown prompt" in error for error in errors)
