from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml

TERMINAL_LOCAL_STATUSES = {
    "completed_in_module",
    "accepted_by_blueprint",
    "superseded",
}

READY_BLUEPRINT_STATUSES = {
    "ready_for_module_pull",
    "in_progress",
    "returned_for_fix",
}

PRIORITY_ALIASES = {
    "critical": "p0",
    "high": "p0",
    "normal": "p1",
    "low": "p2",
    "reference": "p3",
}


@dataclass(frozen=True, slots=True)
class PromptSyncResult:
    active_prompt_id: str | None
    active_prompt_title: str | None
    received_files: tuple[str, ...]
    archived_files: tuple[str, ...]


def load_mapping(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")

    return data


def yaml_text(data: dict[str, Any]) -> str:
    return yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        width=100,
    )


def write_text_if_changed(path: Path, content: str) -> bool:
    normalized = content.rstrip() + "\n"

    if path.exists():
        current = path.read_text(encoding="utf-8")

        if current == normalized:
            return False

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(normalized, encoding="utf-8")
    return True


def write_yaml_if_changed(
    path: Path,
    data: dict[str, Any],
) -> bool:
    return write_text_if_changed(path, yaml_text(data))


def copy_if_changed(source: Path, target: Path) -> bool:
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists() and source.read_bytes() == target.read_bytes():
        return False

    shutil.copyfile(source, target)
    return True


def relative_path(path: Path, project_root: Path) -> str:
    return path.resolve().relative_to(project_root.resolve()).as_posix()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_value(
    project_root: Path,
    *arguments: str,
    fallback: str,
) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=project_root,
        check=False,
        text=True,
        capture_output=True,
    )

    if completed.returncode != 0:
        return fallback

    value = completed.stdout.strip()
    return value or fallback


def sorted_queue(
    blueprint_index: dict[str, Any],
) -> list[dict[str, Any]]:
    queue = blueprint_index.get("prompt_queue")

    if not isinstance(queue, list):
        raise ValueError("Blueprint prompt index must contain prompt_queue list")

    records = [record for record in queue if isinstance(record, dict)]

    return sorted(
        records,
        key=lambda record: int(record.get("sequence", 0)),
    )


def execution_status(record: dict[str, Any]) -> str:
    execution = record.get("module_execution")

    if not isinstance(execution, dict):
        return "planned"

    return str(execution.get("status", "planned"))


def review_status(record: dict[str, Any]) -> str:
    review = record.get("blueprint_review")

    if not isinstance(review, dict):
        return "not_started"

    return str(review.get("status", "not_started"))


def record_file(
    record: dict[str, Any],
    blueprint_module_dir: Path,
) -> Path:
    value = record.get("file")

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Prompt {record.get('prompt_id')} has no file")

    path = blueprint_module_dir / value

    if not path.is_file():
        raise FileNotFoundError(path)

    return path


def existing_prompt_map(
    local_index: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    prompts = local_index.get("prompts")

    if prompts is None:
        return {}

    if not isinstance(prompts, list):
        raise ValueError("Local prompt index prompts must be a list")

    result: dict[str, dict[str, Any]] = {}

    for prompt in prompts:
        if not isinstance(prompt, dict):
            continue

        prompt_id = prompt.get("prompt_id")

        if isinstance(prompt_id, str):
            result[prompt_id] = dict(prompt)

    return result


def choose_active_prompt(
    records: list[dict[str, Any]],
    existing: dict[str, dict[str, Any]],
    requested_prompt_id: str | None,
) -> dict[str, Any] | None:
    by_id = {str(record["prompt_id"]): record for record in records}

    if requested_prompt_id:
        if requested_prompt_id not in by_id:
            raise ValueError(
                f"Requested prompt is not present in Blueprint queue: {requested_prompt_id}"
            )

        return by_id[requested_prompt_id]

    current_active = [
        prompt_id for prompt_id, prompt in existing.items() if prompt.get("status") == "active"
    ]

    if len(current_active) > 1:
        raise ValueError("Local prompt index contains multiple active prompts")

    if current_active:
        active_id = current_active[0]

        if active_id in by_id:
            return by_id[active_id]

    for record in records:
        prompt_id = str(record["prompt_id"])
        local_status = existing.get(
            prompt_id,
            {},
        ).get("status")

        if local_status in TERMINAL_LOCAL_STATUSES:
            continue

        if execution_status(record) in READY_BLUEPRINT_STATUSES:
            return record

    return None


def local_status_for_record(
    record: dict[str, Any],
    existing: dict[str, Any],
    active_prompt_id: str | None,
) -> str:
    prompt_id = str(record["prompt_id"])

    if prompt_id == active_prompt_id:
        return "active"

    current_status = existing.get("status")

    if current_status in TERMINAL_LOCAL_STATUSES:
        return str(current_status)

    if execution_status(record) == "completed_by_module":
        return "completed_in_module"

    if review_status(record) == "accepted_by_blueprint":
        return "accepted_by_blueprint"

    if execution_status(record) in READY_BLUEPRINT_STATUSES:
        return "received"

    return execution_status(record)


def received_date(source_file: Path) -> str:
    prefix = source_file.name[:10]

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", prefix):
        return prefix

    return datetime.now(ZoneInfo("Europe/Kyiv")).date().isoformat()


def build_local_prompt_entry(
    record: dict[str, Any],
    existing: dict[str, Any],
    source_file: Path,
    received_file: Path,
    active_file: Path,
    archived_file: Path,
    project_root: Path,
    module_id: str,
    active_prompt_id: str | None,
) -> dict[str, Any]:
    entry = dict(existing)

    execution = record.get("module_execution")
    review = record.get("blueprint_review")

    execution = execution if isinstance(execution, dict) else {}
    review = review if isinstance(review, dict) else {}

    entry.update(
        {
            "prompt_id": str(record["prompt_id"]),
            "sequence": int(record.get("sequence", 0)),
            "title": str(record.get("title", "")),
            "phase": str(record.get("phase", "")),
            "priority": str(record.get("priority", "normal")),
            "source": "forprint_system_blueprint",
            "source_file": (f"coordination/outgoing_prompts/{module_id}/{record['file']}"),
            "file": relative_path(
                received_file,
                project_root,
            ),
            "status": local_status_for_record(
                record,
                existing,
                active_prompt_id,
            ),
            "received_at": entry.get(
                "received_at",
                received_date(source_file),
            ),
            "module_execution_status": execution_status(record),
            "blueprint_review_status": review_status(record),
        }
    )

    if active_file.is_file():
        entry["active_file"] = relative_path(
            active_file,
            project_root,
        )
    else:
        entry.pop("active_file", None)

    if archived_file.is_file():
        entry["archived_file"] = relative_path(
            archived_file,
            project_root,
        )
    else:
        entry.pop("archived_file", None)

    if not entry.get("completion_report"):
        entry["completion_report"] = execution.get("completion_report")

    if not entry.get("completion_commit"):
        entry["completion_commit"] = execution.get("completion_commit")

    entry["blueprint_acceptance_commit"] = review.get("acceptance_commit")
    entry["blueprint_accepted_at"] = review.get("accepted_at")

    return entry


def render_current_status_markdown(
    record: dict[str, Any],
    branch: str,
    commit: str,
    received_file: Path,
    active_file: Path,
    project_root: Path,
) -> str:
    prompt_id = str(record["prompt_id"])
    title = str(record.get("title", prompt_id))
    phase = str(record.get("phase", "unknown"))
    priority = str(record.get("priority", "normal"))

    return f"""# ForPrint Logistics Service — current status

## Active Blueprint prompt

- Prompt ID: `{prompt_id}`
- Title: {title}
- Phase: `{phase}`
- Priority: `{priority}`
- Branch: `{branch}`
- Intake commit baseline: `{commit}`

## Local prompt paths

- Received copy: `{relative_path(received_file, project_root)}`
- Active copy: `{relative_path(active_file, project_root)}`

## Intake status

The approved Blueprint prompt was synchronized into the module repository,
registered in the local prompt index and activated automatically.

Prompt implementation has not started yet.

## Safety boundary

- No files were written into the Blueprint repository.
- Live provider writes remain disabled.
- No real provider credentials were introduced.
- No canonical client, order, accounting, payment or warehouse ownership was added.

## Next step

Inspect the current module implementation and begin the active prompt through
small tested checkpoints.
"""


def update_current_status(
    status_path: Path,
    status_markdown_path: Path,
    questions_path: Path,
    record: dict[str, Any],
    branch: str,
    commit: str,
    now: datetime,
    received_file: Path,
    active_file: Path,
    project_root: Path,
) -> None:
    status = load_mapping(status_path)

    priority = str(record.get("priority", "normal"))
    phase = str(record.get("phase", ""))
    prompt_id = str(record["prompt_id"])

    status["module_status"] = "active"
    status["priority"] = PRIORITY_ALIASES.get(
        priority,
        priority,
    )
    status["current_phase"] = phase
    status["last_updated"] = now.date().isoformat()
    status["branch"] = branch
    status["last_commit"] = commit
    status["checks"] = {
        "make_check": "not_run",
        "make_check_report": "not_run",
        "governance_check": "not_run",
        "coordination_check": "requires_recheck",
        "tests": "not_run",
    }
    status["recommended_next_step"] = f"implement_{phase}"
    status["status"] = "prompt_active"
    status["phase"] = phase
    status["source_prompt_id"] = prompt_id
    status["updated_at"] = now.isoformat()
    status["implementation_commit"] = None
    status["push_status"] = "not_pushed"

    progress = status.setdefault(
        "progress_summary",
        {},
    )

    if isinstance(progress, dict):
        progress["coordination"] = "active"
        progress["confidence"] = "medium"

    status["prompt_progress"] = {
        "intake": "completed",
        "implementation": "not_started",
        "tests": "not_run",
        "completion": "not_started",
    }
    status["current_step"] = {
        "id": prompt_id,
        "status": "in_progress",
        "next_action": ("inspect current files and implement the active prompt"),
    }
    status["open_questions"] = []

    write_yaml_if_changed(status_path, status)

    write_text_if_changed(
        status_markdown_path,
        render_current_status_markdown(
            record=record,
            branch=branch,
            commit=commit,
            received_file=received_file,
            active_file=active_file,
            project_root=project_root,
        ),
    )

    write_text_if_changed(
        questions_path,
        """# Next questions for ForPrint System Blueprint

No open questions at prompt intake.
""",
    )


def sync_prompt_state(
    *,
    module_id: str,
    blueprint_index_path: Path,
    blueprint_module_dir: Path,
    received_dir: Path,
    active_dir: Path,
    archived_dir: Path,
    local_index_path: Path,
    status_yaml_path: Path,
    status_markdown_path: Path,
    questions_path: Path,
    prompt_id: str | None = None,
    branch: str | None = None,
    commit: str | None = None,
    now: datetime | None = None,
) -> PromptSyncResult:
    project_root = local_index_path.resolve().parents[2]

    blueprint_index = load_mapping(blueprint_index_path)

    if blueprint_index.get("module") != module_id:
        raise ValueError(f"Blueprint prompt index module does not match {module_id}")

    records = sorted_queue(blueprint_index)

    local_index = (
        load_mapping(local_index_path)
        if local_index_path.exists()
        else {
            "schema_version": "module_prompt_index_v0_1",
            "module_id": module_id,
            "prompts": [],
        }
    )

    if local_index.get("module_id") != module_id:
        raise ValueError(f"Local prompt index module_id does not match {module_id}")

    existing = existing_prompt_map(local_index)

    received_dir.mkdir(parents=True, exist_ok=True)
    active_dir.mkdir(parents=True, exist_ok=True)
    archived_dir.mkdir(parents=True, exist_ok=True)

    source_files: dict[str, Path] = {}
    received_files: dict[str, Path] = {}

    for record in records:
        record_prompt_id = str(record["prompt_id"])
        source = record_file(
            record,
            blueprint_module_dir,
        )
        received = received_dir / source.name

        copy_if_changed(source, received)

        source_files[record_prompt_id] = source
        received_files[record_prompt_id] = received

    selected = choose_active_prompt(
        records,
        existing,
        prompt_id,
    )

    active_prompt_id = str(selected["prompt_id"]) if selected is not None else None

    selected_name = source_files[active_prompt_id].name if active_prompt_id is not None else None

    for active_path in active_dir.glob("*.md"):
        if active_path.name == selected_name:
            continue

        archived_path = archived_dir / active_path.name
        copy_if_changed(active_path, archived_path)
        active_path.unlink()

    for record in records:
        record_prompt_id = str(record["prompt_id"])
        local_existing = existing.get(
            record_prompt_id,
            {},
        )

        should_archive = (
            local_existing.get("status") in TERMINAL_LOCAL_STATUSES
            or execution_status(record) == "completed_by_module"
            or review_status(record) == "accepted_by_blueprint"
        )

        if should_archive and record_prompt_id != active_prompt_id:
            archived_path = archived_dir / received_files[record_prompt_id].name
            copy_if_changed(
                received_files[record_prompt_id],
                archived_path,
            )

    active_file_by_id: dict[str, Path] = {}

    if active_prompt_id is not None:
        selected_received = received_files[active_prompt_id]
        selected_active = active_dir / selected_received.name
        selected_archived = archived_dir / selected_received.name

        if selected_archived.exists():
            selected_archived.unlink()

        copy_if_changed(
            selected_received,
            selected_active,
        )

        active_file_by_id[active_prompt_id] = selected_active

    entries: list[dict[str, Any]] = []

    for record in records:
        record_prompt_id = str(record["prompt_id"])
        source = source_files[record_prompt_id]
        received = received_files[record_prompt_id]
        active = active_file_by_id.get(
            record_prompt_id,
            active_dir / source.name,
        )
        archived = archived_dir / source.name

        entry = build_local_prompt_entry(
            record=record,
            existing=existing.get(
                record_prompt_id,
                {},
            ),
            source_file=source,
            received_file=received,
            active_file=active,
            archived_file=archived,
            project_root=project_root,
            module_id=module_id,
            active_prompt_id=active_prompt_id,
        )
        entries.append(entry)

    local_index["schema_version"] = "module_prompt_index_v0_1"
    local_index["module_id"] = module_id
    local_index["active_prompt_id"] = active_prompt_id
    local_index["prompts"] = sorted(
        entries,
        key=lambda entry: int(entry.get("sequence", 0)),
    )

    write_yaml_if_changed(
        local_index_path,
        local_index,
    )

    if selected is not None:
        current_now = now or datetime.now(ZoneInfo("Europe/Kyiv")).replace(microsecond=0)

        current_branch = branch or git_value(
            project_root,
            "branch",
            "--show-current",
            fallback="unknown",
        )
        current_commit = commit or git_value(
            project_root,
            "rev-parse",
            "HEAD",
            fallback="unknown",
        )

        update_current_status(
            status_path=status_yaml_path,
            status_markdown_path=status_markdown_path,
            questions_path=questions_path,
            record=selected,
            branch=current_branch,
            commit=current_commit,
            now=current_now,
            received_file=received_files[active_prompt_id],
            active_file=active_file_by_id[active_prompt_id],
            project_root=project_root,
        )

    return PromptSyncResult(
        active_prompt_id=active_prompt_id,
        active_prompt_title=(str(selected.get("title", "")) if selected is not None else None),
        received_files=tuple(
            relative_path(path, project_root) for path in sorted(received_files.values())
        ),
        archived_files=tuple(
            relative_path(path, project_root) for path in sorted(archived_dir.glob("*.md"))
        ),
    )


def validate_prompt_state(
    *,
    local_index_path: Path,
    status_yaml_path: Path,
    received_dir: Path,
    active_dir: Path,
) -> list[str]:
    errors: list[str] = []

    try:
        local_index = load_mapping(local_index_path)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return [f"Unable to read local prompt index: {exc}"]

    try:
        status = load_mapping(status_yaml_path)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return [f"Unable to read current status: {exc}"]

    prompts = local_index.get("prompts")

    if not isinstance(prompts, list):
        return ["Local prompt index prompts must be a list"]

    project_root = local_index_path.resolve().parents[2]

    prompt_entries = [prompt for prompt in prompts if isinstance(prompt, dict)]

    prompt_ids: list[str] = []

    for entry in prompt_entries:
        prompt_id = entry.get("prompt_id")

        if not isinstance(prompt_id, str) or not prompt_id.strip():
            errors.append("Every prompt entry must contain a non-empty prompt_id")
            continue

        prompt_ids.append(prompt_id)

        received_value = entry.get("file")

        if not isinstance(received_value, str) or not received_value.strip():
            errors.append(f"Prompt {prompt_id} has no received file path")
            continue

        received_path = project_root / received_value

        if not received_path.is_file():
            errors.append(f"Received prompt file is missing for {prompt_id}: {received_value}")

    if len(prompt_ids) != len(set(prompt_ids)):
        errors.append("Local prompt index contains duplicate prompt_id values")

    active_files = sorted(active_dir.glob("*.md"))
    active_entries = [entry for entry in prompt_entries if entry.get("status") == "active"]

    active_prompt_id = local_index.get("active_prompt_id")
    status_value = status.get("status")

    active_mode = bool(
        active_files
        or active_entries
        or active_prompt_id is not None
        or status_value == "prompt_active"
    )

    if active_mode:
        if len(active_files) != 1:
            errors.append(
                "coordination/prompts/active must "
                "contain exactly one Markdown prompt "
                "in active mode"
            )

        if len(active_entries) != 1:
            errors.append(
                "Local prompt index must contain exactly one active prompt entry in active mode"
            )

        if not isinstance(active_prompt_id, str) or not active_prompt_id.strip():
            errors.append("active_prompt_id must identify the active prompt in active mode")

        if status_value != "prompt_active":
            errors.append("Current status must be prompt_active when an active prompt exists")

        if len(active_files) == 1 and len(active_entries) == 1:
            active_file = active_files[0]
            entry = active_entries[0]
            entry_prompt_id = entry.get("prompt_id")

            if active_prompt_id != entry_prompt_id:
                errors.append("active_prompt_id does not match the active prompt entry")

            if status.get("source_prompt_id") != entry_prompt_id:
                errors.append("Current status source_prompt_id does not match the active prompt")

            expected_active = entry.get("active_file")

            if (
                not isinstance(
                    expected_active,
                    str,
                )
                or not expected_active.strip()
            ):
                errors.append("Active prompt entry has no active_file path")
            else:
                expected_active_path = project_root / expected_active

                if expected_active_path.resolve() != active_file.resolve():
                    errors.append("Active prompt file does not match index active_file")

            received_value = entry.get("file")

            if isinstance(received_value, str):
                received_file = project_root / received_value

                if received_file.is_file() and file_hash(active_file) != file_hash(received_file):
                    errors.append("Active prompt differs from its received copy")

        return errors

    # Terminal mode is valid after module completion:
    # no active file, no active entry and no active ID.
    if active_files:
        errors.append(
            "Completed prompt state must not contain files in coordination/prompts/active"
        )

    if active_entries:
        errors.append("Completed prompt state must not contain an active prompt index entry")

    if active_prompt_id is not None:
        errors.append("active_prompt_id must be null when no prompt is active")

    if status_value not in TERMINAL_LOCAL_STATUSES:
        errors.append("No active prompt exists, but current status is not a terminal prompt status")

    source_prompt_id = status.get("source_prompt_id")

    if not isinstance(source_prompt_id, str) or not source_prompt_id.strip():
        errors.append("Terminal current status must contain source_prompt_id")
        return errors

    matching_entries = [
        entry for entry in prompt_entries if entry.get("prompt_id") == source_prompt_id
    ]

    if len(matching_entries) != 1:
        errors.append("Terminal current status must match exactly one prompt index entry")
        return errors

    entry = matching_entries[0]
    entry_status = entry.get("status")

    if entry_status not in TERMINAL_LOCAL_STATUSES:
        errors.append("Terminal prompt index entry must have a terminal local status")

    if "active_file" in entry:
        errors.append("Terminal prompt entry must not retain active_file")

    archived_value = entry.get("archived_file")

    if not isinstance(archived_value, str) or not archived_value.strip():
        errors.append("Terminal prompt entry must contain archived_file")
    else:
        archived_file = project_root / archived_value

        if not archived_file.is_file():
            errors.append(f"Archived prompt file is missing: {archived_value}")
        else:
            received_value = entry.get("file")

            if isinstance(received_value, str):
                received_file = project_root / received_value

                if received_file.is_file() and file_hash(archived_file) != file_hash(received_file):
                    errors.append("Archived prompt differs from its received copy")

    if entry_status == "completed_in_module":
        if entry.get("module_execution_status") != "completed_by_module":
            errors.append(
                "Completed module prompt must record module_execution_status as completed_by_module"
            )

        if not entry.get("completion_report"):
            errors.append("Completed module prompt must contain completion_report")

        if not entry.get("completion_commit"):
            errors.append("Completed module prompt must contain completion_commit")

    prompt_progress = status.get("prompt_progress")

    if isinstance(prompt_progress, dict) and prompt_progress.get("completion") != "completed":
        errors.append("Terminal prompt status must record prompt_progress.completion as completed")

    return errors


def print_prompt_status(
    local_index_path: Path,
) -> int:
    data = load_mapping(local_index_path)
    prompts = data.get("prompts", [])

    active = [
        prompt
        for prompt in prompts
        if isinstance(prompt, dict) and prompt.get("status") == "active"
    ]

    if len(active) != 1:
        print("Active prompt: invalid or missing")
        return 1

    prompt = active[0]

    print("Active local prompt")
    print(f"Prompt ID: {prompt['prompt_id']}")
    print(f"Title: {prompt.get('title', '')}")
    print(f"Phase: {prompt.get('phase', '')}")
    print(f"Priority: {prompt.get('priority', '')}")
    print(f"Received: {prompt.get('file', '')}")
    print(f"Active: {prompt.get('active_file', '')}")
    print(f"Blueprint module status: {prompt.get('module_execution_status', '')}")
    print(f"Blueprint review status: {prompt.get('blueprint_review_status', '')}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=("Synchronize and activate the current Logistics Service Blueprint prompt.")
    )
    parser.add_argument(
        "--module-id",
        default="logistics_service",
    )
    parser.add_argument(
        "--blueprint-index",
        type=Path,
        default=Path(
            "/srv/software_development/forprint-project/"
            "forprint_system_blueprint/coordination/"
            "outgoing_prompts/logistics_service/index.yaml"
        ),
    )
    parser.add_argument(
        "--blueprint-module-dir",
        type=Path,
        default=Path(
            "/srv/software_development/forprint-project/"
            "forprint_system_blueprint/coordination/"
            "outgoing_prompts/logistics_service"
        ),
    )
    parser.add_argument(
        "--received-dir",
        type=Path,
        default=Path("coordination/prompts/received"),
    )
    parser.add_argument(
        "--active-dir",
        type=Path,
        default=Path("coordination/prompts/active"),
    )
    parser.add_argument(
        "--archived-dir",
        type=Path,
        default=Path("coordination/prompts/archived"),
    )
    parser.add_argument(
        "--local-index",
        type=Path,
        default=Path("coordination/prompts/index.yaml"),
    )
    parser.add_argument(
        "--status-yaml",
        type=Path,
        default=Path("coordination/status/current_status.yaml"),
    )
    parser.add_argument(
        "--status-md",
        type=Path,
        default=Path("coordination/status/current_status.md"),
    )
    parser.add_argument(
        "--questions-md",
        type=Path,
        default=Path("coordination/status/next_questions_for_blueprint.md"),
    )
    parser.add_argument("--prompt-id")
    parser.add_argument(
        "--check-only",
        action="store_true",
    )
    parser.add_argument(
        "--status-only",
        action="store_true",
    )
    args = parser.parse_args()

    if args.status_only:
        return print_prompt_status(args.local_index)

    if args.check_only:
        errors = validate_prompt_state(
            local_index_path=args.local_index,
            status_yaml_path=args.status_yaml,
            received_dir=args.received_dir,
            active_dir=args.active_dir,
        )

        if errors:
            print("Prompt state check failed:")

            for error in errors:
                print(f"  - {error}")

            return 1

        print("Prompt state check passed.")
        return 0

    try:
        result = sync_prompt_state(
            module_id=args.module_id,
            blueprint_index_path=(args.blueprint_index),
            blueprint_module_dir=(args.blueprint_module_dir),
            received_dir=args.received_dir,
            active_dir=args.active_dir,
            archived_dir=args.archived_dir,
            local_index_path=args.local_index,
            status_yaml_path=args.status_yaml,
            status_markdown_path=args.status_md,
            questions_path=args.questions_md,
            prompt_id=args.prompt_id,
        )
    except (
        FileNotFoundError,
        OSError,
        ValueError,
        yaml.YAMLError,
    ) as exc:
        print(f"Prompt synchronization failed: {exc}")
        return 1

    print("Blueprint prompts synchronized.")
    print(f"Active prompt: {result.active_prompt_id or 'none'}")

    for path in result.received_files:
        print(f"Received: {path}")

    for path in result.archived_files:
        print(f"Archived: {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
