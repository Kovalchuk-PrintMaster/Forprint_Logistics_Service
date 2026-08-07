from __future__ import annotations

import argparse
import shutil
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


def _markdown_list(
    items: list[Any],
    *,
    empty: str = "None.",
) -> str:
    if not items:
        return f"- {empty}"

    return "\n".join(f"- {item}" for item in items)


def _render_completion_report(packet: dict[str, Any]) -> str:
    frontmatter = {
        "schema_version": packet["schema_version"],
        "protocol_version": packet["protocol_version"],
        "report_id": packet["report_id"],
        "prompt_id": packet["prompt_id"],
        "target_module": packet["module_id"],
        "phase": packet["phase"],
        "completed_step": packet["completion_id"],
        "status": "completed_in_module",
        "blueprint_review_status": "not_started",
        "automatic_acceptance": False,
        "implementation_commit": packet["implementation_commit"],
        "branch": packet["branch"],
        "push_status": packet["push_status"],
        "supersedes_completion_id": packet.get("supersedes_completion_id"),
        "revision_reason": packet.get("revision_reason"),
        "checks": packet["checks"],
        "boundary_confirmation": packet["boundary_confirmation"],
        "blockers": packet["blockers"],
        "dependency_implications": packet["dependency_implications"],
        "completion_evidence_complete": packet["completion_evidence_complete"],
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

    if packet.get("supersedes_completion_id") is None:
        superseding_text = "- This completion packet does not supersede prior evidence."
    else:
        superseding_text = "\n".join(
            (
                f"- Supersedes completion ID: `{packet['supersedes_completion_id']}`",
                f"- Revision reason: {packet['revision_reason']}",
            )
        )

    return f"""---
{frontmatter_text}
---

# {packet["module_name"]} completion report

## Current completion protocol

- Schema: `{packet["schema_version"]}`
- Intake protocol: `{packet["protocol_version"]}`
- Blueprint review status: `not_started`
- Automatic acceptance: `false`

`READY_FOR_OPERATOR_REVIEW` is an intake status, not `ACCEPTED`.

## Prompt

- Prompt ID: `{packet["prompt_id"]}`
- Completion ID: `{packet["completion_id"]}`
- Phase: `{packet["phase"]}`
- Branch: `{packet["branch"]}`
- Implementation commit: `{packet["implementation_commit"]}`
- Push status: `{packet["push_status"]}`
- Created at: `{packet["created_at"]}`

## Superseding evidence

{superseding_text}

Historical completion packets remain immutable.

## Summary

{packet["summary"]}

## Implemented

{_markdown_list(packet["implemented"])}

## Files changed and current outputs

{_markdown_list(files_changed)}

## Checks passed

{_markdown_list([f"{name}: {status}" for name, status in packet["checks"].items()])}

## Completion evidence

- Complete: `{str(packet["completion_evidence_complete"]).lower()}`

## Blockers

{_markdown_list(packet["blockers"], empty="No blockers.")}

## Dependency implications

{_markdown_list(packet["dependency_implications"], empty="No dependency implications.")}

## Instruction sources reviewed

{_markdown_list(packet["instruction_sources_reviewed"])}

## Standards reviewed

{_markdown_list(packet["standards_reviewed"])}

## Standards alignment notes

{_markdown_list(packet["standards_alignment_notes"])}

## Boundary confirmation

{_markdown_list([f"{name}: {value}" for name, value in packet["boundary_confirmation"].items()])}

## Blueprint boundary

No files were written directly into the ForPrint System Blueprint repository.
This module completion does not create an `ACCEPT` decision.

## Recommended next steps

{_markdown_list(packet["next_recommended_steps"])}

## Open questions for Blueprint

{_markdown_list(packet["next_questions_for_blueprint"], empty="No open questions.")}
"""


def _render_current_status_markdown(packet: dict[str, Any]) -> str:
    return f"""# ForPrint Logistics Service — current status

## Current completion protocol

- Schema: `{packet["schema_version"]}`
- Intake protocol: `{packet["protocol_version"]}`
- Blueprint review: `not_started`
- Automatic acceptance: `false`

## Current phase

`{packet["phase"]}`

## Module state

The work item `{packet["prompt_id"]}` is completed inside the module
repository and is pending Blueprint intake/review.

Implementation commit:

`{packet["implementation_commit"]}`

The completion commit is intentionally derived after Git commit/publication
and is passed separately to Blueprint intake. It is not recursively embedded
into the packet.

## Summary

{packet["summary"]}

## Current outputs

{_markdown_list(packet["current_outputs"])}

## Safety boundary

{_markdown_list([f"{name}: {value}" for name, value in packet["boundary_confirmation"].items()])}

## Blockers

{_markdown_list(packet["blockers"], empty="No blockers.")}

## Dependency implications

{_markdown_list(packet["dependency_implications"], empty="No dependency implications.")}

## Recommended next steps

{_markdown_list(packet["next_recommended_steps"])}

## Open questions

{_markdown_list(packet["next_questions_for_blueprint"], empty="No open questions.")}

`READY_FOR_OPERATOR_REVIEW` does not equal `ACCEPTED`.
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
    data["completion_commit"] = None
    data["completion_commit_status"] = "derive_after_git_commit"
    data["push_status"] = packet["push_status"]
    data["blueprint_review_status"] = "not_started"
    data["automatic_acceptance"] = False

    data["completion_protocol"] = {
        "schema_version": packet["schema_version"],
        "protocol_version": packet["protocol_version"],
        "supersedes_completion_id": packet.get("supersedes_completion_id"),
        "revision_reason": packet.get("revision_reason"),
    }

    data["checks"] = {
        "make_check": "ok",
        "make_check_report": packet["checks"]["check_report"],
        "governance_check": packet["checks"]["governance_check"],
        "coordination_check": "ok",
        "tests": packet["checks"]["tests"],
    }

    boundary = packet["boundary_confirmation"]

    data["boundary"] = {
        "no_foreign_ownership": True,
        "no_production_api": boundary["no_production_api"],
        "no_live_write": boundary["no_production_write"],
        "no_real_integrations": boundary["no_live_external_integrations"],
        "no_automatic_posting": boundary["no_automatic_posting"],
        "no_real_1c_sync": boundary["no_real_1c_sync"],
    }

    data["boundaries"] = dict(boundary)
    data["blockers"] = list(packet["blockers"])
    data["dependency_implications"] = list(packet["dependency_implications"])
    data["completion_evidence_complete"] = packet["completion_evidence_complete"]

    progress = data.setdefault("progress_summary", {})
    progress.update(
        {
            "documentation": "completed",
            "coordination": "completed",
            "confidence": "high",
        }
    )

    data["current_step"] = {
        "id": packet["completion_id"],
        "status": "completed_in_module",
        "next_action": packet["next_recommended_steps"][0],
    }
    data["open_questions"] = packet["next_questions_for_blueprint"]
    data["prompt_progress"] = {
        "intake": "completed",
        "implementation": "completed",
        "tests": "passed",
        "completion": "completed",
    }

    return _write_yaml_if_changed(path, data)


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
    matching_prompt.setdefault(
        "blueprint_review_status",
        "not_started",
    )
    matching_prompt["completion_report"] = packet["report_path"]
    matching_prompt["implementation_commit"] = packet["implementation_commit"]
    matching_prompt["completion_commit"] = None
    matching_prompt["completion_commit_status"] = "derive_after_git_commit"
    matching_prompt["completion_schema_version"] = packet["schema_version"]
    matching_prompt["completion_protocol_version"] = packet["protocol_version"]

    if packet.get("supersedes_completion_id") is not None:
        matching_prompt["supersedes_completion_id"] = packet["supersedes_completion_id"]
        matching_prompt["revision_reason"] = packet["revision_reason"]

    active_file_value = matching_prompt.pop(
        "active_file",
        None,
    )

    if active_file_value:
        active_relative = Path(str(active_file_value))
        active_path = root / active_relative

        if active_path.is_file():
            archived_relative = Path("coordination/prompts/archived") / active_path.name
            archived_path = root / archived_relative
            archived_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            if archived_path.exists():
                if archived_path.read_text(encoding="utf-8") != active_path.read_text(
                    encoding="utf-8"
                ):
                    raise ValueError(
                        f"Archived prompt exists with different content: {archived_relative}"
                    )
                active_path.unlink()
            else:
                shutil.move(str(active_path), str(archived_path))

            matching_prompt["archived_file"] = str(archived_relative)
            changed.extend([active_path, archived_path])

    if data.get("active_prompt_id") == packet["prompt_id"]:
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
    reports = data.get("reports")

    if not isinstance(reports, list):
        raise ValueError("coordination/reports/index.yaml reports must be a list")

    record = {
        "report_id": packet["report_id"],
        "prompt_id": packet["prompt_id"],
        "type": "completion",
        "report_file": packet["report_path"],
        "phase": packet["phase"],
        "status": "completed_in_module",
        "implementation_commit": packet["implementation_commit"],
        "completion_commit": None,
        "completion_commit_status": "derive_after_git_commit",
        "schema_version": packet["schema_version"],
        "protocol_version": packet["protocol_version"],
        "supersedes_completion_id": packet.get("supersedes_completion_id"),
        "revision_reason": packet.get("revision_reason"),
        "completion_evidence_complete": packet["completion_evidence_complete"],
        "blueprint_review_status": "not_started",
        "automatic_acceptance": False,
    }

    existing: dict[str, Any] | None = None

    for item in reports:
        if isinstance(item, dict) and (item.get("report_id") == packet["report_id"]):
            existing = item
            break

    if existing is None:
        reports.append(record)
    else:
        existing.clear()
        existing.update(record)

    return _write_yaml_if_changed(path, data)


def apply_completion_packet(
    packet_path: Path,
    project_root: Path | None = None,
) -> list[Path]:
    root = project_root.resolve() if project_root is not None else PROJECT_ROOT
    packet_path = packet_path.resolve()

    packet = load_packet(packet_path)
    errors = validate_packet(packet)

    if errors:
        raise ValueError("Completion packet validation failed:\n- " + "\n- ".join(errors))

    changed: list[Path] = []

    report_path = root / packet["report_path"]

    if _write_text_if_changed(
        report_path,
        _render_completion_report(packet),
    ):
        changed.append(report_path)

    if _update_current_status(root, packet):
        changed.append(root / "coordination/status/current_status.yaml")

    changed.extend(_update_prompts_index(root, packet))

    if _update_reports_index(root, packet):
        changed.append(root / "coordination/reports/index.yaml")

    status_md = root / "coordination/status/current_status.md"

    if _write_text_if_changed(
        status_md,
        _render_current_status_markdown(packet),
    ):
        changed.append(status_md)

    questions_md = root / "coordination/status/next_questions_for_blueprint.md"

    if _write_text_if_changed(
        questions_md,
        _render_questions(packet),
    ):
        changed.append(questions_md)

    deduplicated: list[Path] = []
    seen: set[Path] = set()

    for path in changed:
        resolved = path.resolve()

        if resolved in seen:
            continue

        seen.add(resolved)
        deduplicated.append(resolved)

    return deduplicated


def main() -> int:
    parser = argparse.ArgumentParser(
        description=("Apply a current Logistics Service v0.2 completion packet.")
    )
    parser.add_argument("packet", type=Path)
    parser.add_argument(
        "--root",
        type=Path,
        default=PROJECT_ROOT,
    )
    args = parser.parse_args()

    try:
        changed = apply_completion_packet(
            args.packet,
            args.root,
        )
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"Completion packet apply failed: {exc}")
        return 1

    if not changed:
        print("Completion packet apply is idempotent: no changes required.")
        return 0

    print("Completion packet applied. Changed files:")

    for path in changed:
        try:
            relative = path.relative_to(args.root.resolve())
        except ValueError:
            relative = path

        print(f"  - {relative}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
