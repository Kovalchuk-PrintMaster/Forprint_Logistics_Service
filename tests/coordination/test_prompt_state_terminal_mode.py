from __future__ import annotations

from pathlib import Path

import yaml

from scripts.coordination.sync_prompt_state import (
    validate_prompt_state,
)

PROMPT_ID = "logistics_service_boundary_and_local_model_v0_1"
PROMPT_NAME = "2026-07-11__logistics_service__boundary_and_local_model_v0_1.md"


def write_yaml(
    path: Path,
    data: dict[str, object],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        yaml.safe_dump(
            data,
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )


def prepare_terminal_state(
    root: Path,
) -> dict[str, Path]:
    received = root / "coordination/prompts/received"
    active = root / "coordination/prompts/active"
    archived = root / "coordination/prompts/archived"

    received.mkdir(parents=True)
    active.mkdir(parents=True)
    archived.mkdir(parents=True)

    prompt_content = "# Completed prompt\n"

    received_file = received / PROMPT_NAME
    archived_file = archived / PROMPT_NAME

    received_file.write_text(
        prompt_content,
        encoding="utf-8",
    )
    archived_file.write_text(
        prompt_content,
        encoding="utf-8",
    )

    local_index = root / "coordination/prompts/index.yaml"
    status = root / "coordination/status/current_status.yaml"

    write_yaml(
        local_index,
        {
            "schema_version": ("module_prompt_index_v0_1"),
            "module_id": "logistics_service",
            "prompts": [
                {
                    "prompt_id": PROMPT_ID,
                    "status": ("completed_in_module"),
                    "module_execution_status": ("completed_by_module"),
                    "blueprint_review_status": ("not_started"),
                    "file": (f"coordination/prompts/received/{PROMPT_NAME}"),
                    "archived_file": (f"coordination/prompts/archived/{PROMPT_NAME}"),
                    "completion_report": ("coordination/reports/completion/report.md"),
                    "completion_commit": ("abcdef1234567890"),
                }
            ],
            "active_prompt_id": None,
        },
    )

    write_yaml(
        status,
        {
            "schema_version": ("module_status_v0_1"),
            "module_id": "logistics_service",
            "status": ("completed_in_module"),
            "source_prompt_id": PROMPT_ID,
            "prompt_progress": {
                "intake": "completed",
                "implementation": "completed",
                "tests": "passed",
                "completion": "completed",
            },
        },
    )

    return {
        "local_index": local_index,
        "status": status,
        "received": received,
        "active": active,
        "archived": archived,
    }


def validate(
    paths: dict[str, Path],
) -> list[str]:
    return validate_prompt_state(
        local_index_path=paths["local_index"],
        status_yaml_path=paths["status"],
        received_dir=paths["received"],
        active_dir=paths["active"],
    )


def test_terminal_prompt_state_is_valid(
    tmp_path: Path,
) -> None:
    paths = prepare_terminal_state(tmp_path)

    assert validate(paths) == []


def test_terminal_state_rejects_dangling_active_id(
    tmp_path: Path,
) -> None:
    paths = prepare_terminal_state(tmp_path)

    index = yaml.safe_load(paths["local_index"].read_text(encoding="utf-8"))
    index["active_prompt_id"] = PROMPT_ID
    write_yaml(
        paths["local_index"],
        index,
    )

    errors = validate(paths)

    assert any("exactly one Markdown prompt" in error for error in errors)
    assert any("exactly one active prompt entry" in error for error in errors)


def test_terminal_state_requires_archived_copy(
    tmp_path: Path,
) -> None:
    paths = prepare_terminal_state(tmp_path)

    (paths["archived"] / PROMPT_NAME).unlink()

    errors = validate(paths)

    assert any("Archived prompt file is missing" in error for error in errors)
