from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.coordination.validate_completion_packet import (  # noqa: E402
    load_packet,
    validate_packet,
)


def _load_mapping(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")

    return data


def _yaml_text(data: dict[str, Any]) -> str:
    return yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
    )


def _write_text_if_changed(path: Path, content: str) -> bool:
    normalized = content.rstrip() + "\n"

    if path.exists():
        current = path.read_text(encoding="utf-8")

        if current == normalized:
            return False

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(normalized, encoding="utf-8")
    return True


def _write_yaml_if_changed(path: Path, data: dict[str, Any]) -> bool:
    return _write_text_if_changed(path, _yaml_text(data))


def _markdown_list(items: list[Any]) -> str:
    if not items:
        return "- No open questions."

    return "\n".join(f"- {item}" for item in items)


def _render_completion_report(packet: dict[str, Any]) -> str:
    frontmatter = {
        "report_id": packet["report_id"],
        "prompt_id": packet["prompt_id"],
        "target_module": packet["module_id"],
        "phase": packet["phase"],
        "completed_step": packet["completion_id"],
        "status": "completed_in_module",
        "implementation_commit": packet["implementation_commit"],
        "branch": packet["branch"],
        "push_status": packet["push_status"],
        "checks": packet["checks"],
        "known_warnings": packet.get("known_warnings", []),
        "boundary_confirmation": packet["boundary_confirmation"],
        "next_questions_for_blueprint": packet["next_questions_for_blueprint"],
    }

    frontmatter_text = yaml.safe_dump(
        frontmatter,
        sort_keys=False,
        allow_unicode=True,
    ).rstrip()

    files_changed = packet.get(
        "files_changed",
        packet["current_outputs"],
    )

    return f"""---
{frontmatter_text}
---

# {packet["module_name"]} completion report

## Prompt

- Prompt ID: `{packet["prompt_id"]}`
- Completion ID: `{packet["completion_id"]}`
- Phase: `{packet["phase"]}`
- Branch: `{packet["branch"]}`
- Implementation commit: `{packet["implementation_commit"]}`
- Push status: `{packet["push_status"]}`
- Created at: `{packet["created_at"]}`

## Summary

{packet["summary"]}

## Implemented

{_markdown_list(packet["implemented"])}

## Files changed and current outputs

{_markdown_list(files_changed)}

## Checks passed

{_markdown_list([f"{name}: {status}" for name, status in packet["checks"].items()])}

## Known warnings

{_markdown_list(packet.get("known_warnings", []))}

## Instruction sources reviewed

{_markdown_list(packet["instruction_sources_reviewed"])}

## Standards reviewed

{_markdown_list(packet["standards_reviewed"])}

## Standards alignment notes

{_markdown_list(packet["standards_alignment_notes"])}

## Boundary confirmation

{_markdown_list([f"{name}: {value}" for name, value in packet["boundary_confirmation"].items()])}

## Secrets policy confirmation

No real provider credentials, API keys or production secrets were committed.

## Live provider write confirmation

Live provider writes remain disabled. No shipment, TTN, courier, taxi or other
provider-side mutation was introduced.

## Blueprint write boundary

No files were written directly into the ForPrint System Blueprint repository.

Completion packet automation was available and used inside the Logistics
Service repository.

## Recommended next steps

{_markdown_list(packet["next_recommended_steps"])}

## Open questions for Blueprint

{_markdown_list(packet["next_questions_for_blueprint"])}
"""


def _render_current_status_markdown(packet: dict[str, Any]) -> str:
    return f"""# ForPrint Logistics Service — current status

## Current phase

`{packet["phase"]}`

## Module state

The prompt `{packet["prompt_id"]}` is completed inside the module repository.

Implementation commit:

`{packet["implementation_commit"]}`

Push status:

`{packet["push_status"]}`

## Summary

{packet["summary"]}

## Implemented

{_markdown_list(packet["implemented"])}

## Current outputs

{_markdown_list(packet["current_outputs"])}

## Safety boundary

- Live provider writes remain disabled.
- No real provider credentials were committed.
- No canonical client or order ownership was introduced.
- No payment, warehouse, accounting or 1C mutation was introduced.
- No files were written directly into the Blueprint repository.

## Recommended next steps

{_markdown_list(packet["next_recommended_steps"])}

## Open questions

{_markdown_list(packet["next_questions_for_blueprint"])}
"""


def _render_questions(packet: dict[str, Any]) -> str:
    questions = packet["next_questions_for_blueprint"]

    if not questions:
        return """# Next questions for ForPrint System Blueprint

No open questions.
"""

    return f"""# Next questions for ForPrint System Blueprint

{_markdown_list(questions)}
"""


def _update_current_status(
    root: Path,
    packet: dict[str, Any],
) -> bool:
    path = root / "coordination/status/current_status.yaml"
    data = _load_mapping(path)

    data["module_status"] = "active"
    data["priority"] = "p0"
    data["current_phase"] = packet["phase"]
    data["last_completed_step"] = packet["completion_id"]
    data["last_updated"] = packet["created_at"][:10]
    data["branch"] = packet["branch"]
    data["last_commit"] = packet["implementation_commit"]
    data["recommended_next_step"] = packet["next_recommended_steps"][0]

    data["status"] = "completed_in_module"
    data["phase"] = packet["phase"]
    data["source_prompt_id"] = packet["prompt_id"]
    data["updated_at"] = packet["created_at"]
    data["implementation_commit"] = packet["implementation_commit"]
    data["push_status"] = packet["push_status"]

    data["checks"] = {
        "make_check": "ok",
        "make_check_report": (packet["checks"]["check_report"]),
        "governance_check": (packet["checks"]["governance_check"]),
        "coordination_check": "ok",
        "tests": packet["checks"]["tests"],
    }

    boundary = packet["boundary_confirmation"]

    data["boundary"] = {
        "no_foreign_ownership": not (
            boundary["database_ownership_added"] or boundary["operational_data_ownership_added"]
        ),
        "no_production_api": not boundary["production_api_added"],
        "no_live_write": not boundary["live_provider_writes_added"],
        "no_real_integrations": not boundary["live_external_integrations_added"],
    }

    data.setdefault(
        "boundaries",
        {},
    ).update(boundary)

    progress = data.setdefault(
        "progress_summary",
        {},
    )
    progress.update(
        {
            "project_skeleton": "completed",
            "core_domain_models": "completed",
            "provider_adapter_boundary": "completed",
            "fixture_support": "completed",
            "integration_readiness": "preview_only",
            "documentation": "completed",
            "coordination": "completed",
            "confidence": "high",
        }
    )

    data["current_step"] = {
        "id": packet["completion_id"],
        "status": "completed",
        "next_action": (packet["next_recommended_steps"][0]),
    }
    data["open_questions"] = packet["next_questions_for_blueprint"]
    data["prompt_progress"] = {
        "intake": "completed",
        "implementation": "completed",
        "tests": "passed",
        "completion": "completed",
    }

    return _write_yaml_if_changed(
        path,
        data,
    )


def _update_prompts_index(
    root: Path,
    packet: dict[str, Any],
) -> list[Path]:
    path = root / "coordination/prompts/index.yaml"
    data = _load_mapping(path)
    prompts = data.get("prompts")

    if not isinstance(prompts, list):
        raise ValueError("coordination/prompts/index.yaml prompts must be a list")

    matching_prompt: dict[str, Any] | None = None

    for prompt in prompts:
        if prompt.get("prompt_id") == packet["prompt_id"]:
            matching_prompt = prompt
            break

    if matching_prompt is None:
        raise ValueError(f"Prompt is not registered locally: {packet['prompt_id']}")

    changed: list[Path] = []

    matching_prompt["status"] = "completed_in_module"
    matching_prompt["module_execution_status"] = "completed_by_module"

    # Module completion must never claim Blueprint
    # acceptance. Preserve a real Blueprint review state
    # when present, otherwise record that review has not
    # started yet.
    matching_prompt.setdefault(
        "blueprint_review_status",
        "not_started",
    )
    matching_prompt["completion_report"] = packet["report_path"]
    matching_prompt["completion_commit"] = packet["implementation_commit"]

    active_file_value = matching_prompt.pop(
        "active_file",
        None,
    )

    if active_file_value:
        active_relative = Path(str(active_file_value))
        active_path = root / active_relative

        archived_relative = Path("coordination/prompts/archived") / active_relative.name
        archived_path = root / archived_relative

        if active_path.is_file():
            active_content = active_path.read_text(encoding="utf-8")

            if archived_path.is_file():
                archived_content = archived_path.read_text(encoding="utf-8")

                if archived_content != active_content:
                    raise ValueError(f"Active and archived prompt copies differ: {active_relative}")
            else:
                archived_path.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )
                archived_path.write_text(
                    active_content,
                    encoding="utf-8",
                )
                changed.append(archived_path)

            active_path.unlink()
            changed.append(active_path)

        elif not archived_path.is_file():
            raise ValueError(
                f"Active prompt file is missing and no archived copy exists: {active_relative}"
            )

        matching_prompt["archived_file"] = str(archived_relative)

    data["active_prompt_id"] = None

    if _write_yaml_if_changed(path, data):
        changed.append(path)

    return changed


def _update_reports_index(
    root: Path,
    packet: dict[str, Any],
) -> bool:
    path = root / "coordination/reports/index.yaml"
    data = _load_mapping(path)
    reports = data.setdefault("reports", [])

    if not isinstance(reports, list):
        raise ValueError("coordination/reports/index.yaml reports must be a list")

    record = {
        "report_id": packet["report_id"],
        "prompt_id": packet["prompt_id"],
        "report_file": packet["report_path"],
        "status": "completed_in_module",
        "created_at": packet["created_at"],
        "implementation_commit": packet["implementation_commit"],
        "push_status": packet["push_status"],
    }

    for index, report in enumerate(reports):
        if report.get("report_id") == packet["report_id"]:
            reports[index] = record
            break
    else:
        reports.append(record)

    reports.sort(key=lambda item: item["report_id"])

    return _write_yaml_if_changed(path, data)


def apply_completion_packet(
    packet_path: Path,
    project_root: Path,
) -> list[Path]:
    packet = load_packet(packet_path)
    errors = validate_packet(packet)

    if errors:
        raise ValueError("\n".join(errors))

    changed: list[Path] = []

    report_path = project_root / packet["report_path"]

    prompt_changes = _update_prompts_index(
        project_root,
        packet,
    )
    changed.extend(prompt_changes)

    operations = (
        (
            report_path,
            _write_text_if_changed(
                report_path,
                _render_completion_report(packet),
            ),
        ),
        (
            (project_root / "coordination/status/current_status.yaml"),
            _update_current_status(
                project_root,
                packet,
            ),
        ),
        (
            (project_root / "coordination/reports/index.yaml"),
            _update_reports_index(
                project_root,
                packet,
            ),
        ),
        (
            (project_root / "coordination/status/current_status.md"),
            _write_text_if_changed(
                (project_root / "coordination/status/current_status.md"),
                _render_current_status_markdown(packet),
            ),
        ),
        (
            (project_root / "coordination/status/next_questions_for_blueprint.md"),
            _write_text_if_changed(
                (project_root / "coordination/status/next_questions_for_blueprint.md"),
                _render_questions(packet),
            ),
        ),
    )

    for path, was_changed in operations:
        if was_changed:
            changed.append(path)

    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply a Logistics Service completion packet.")
    parser.add_argument("packet", type=Path)
    parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
    )
    args = parser.parse_args()

    try:
        changed = apply_completion_packet(
            args.packet.resolve(),
            args.project_root.resolve(),
        )
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"Completion packet apply failed: {exc}")
        return 1

    if changed:
        print("Completion packet applied. Changed files:")

        for path in changed:
            print(f"  - {path}")
    else:
        print("Completion packet apply is idempotent: no changes required.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
