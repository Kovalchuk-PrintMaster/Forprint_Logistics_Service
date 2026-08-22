from __future__ import annotations

import argparse
import hashlib
import subprocess
from pathlib import Path
from typing import Any

import yaml

READY = "ready_for_module_pull"


class H9Error(RuntimeError):
    pass


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise H9Error(f"missing required file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise H9Error(f"YAML root must be mapping: {path}")
    return data


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_bytes_if_changed(path: Path, data: bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() == data:
        return False
    path.write_bytes(data)
    return True


def write_yaml_if_changed(path: Path, data: dict[str, Any]) -> bool:
    return write_bytes_if_changed(
        path,
        yaml.safe_dump(
            data,
            sort_keys=False,
            allow_unicode=True,
            width=100,
        ).encode("utf-8"),
    )


def git(root: Path, *args: str) -> str:
    cp = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if cp.returncode != 0:
        raise H9Error(f"git {' '.join(args)} failed: {cp.stdout}{cp.stderr}")
    return cp.stdout.strip()


def release_summary(data: dict[str, Any]) -> dict[str, Any]:
    release = data.get("release")
    scope = data.get("module_scope")
    legacy = data.get("legacy_compatibility")
    if not all(isinstance(item, dict) for item in (release, scope, legacy)):
        raise H9Error("current release projection is structurally invalid")
    return {
        "base_release": release.get("base_release"),
        "base_release_state": release.get("base_release_state"),
        "hardening_release": release.get("hardening_release"),
        "hardening_state": release.get("hardening_state"),
        "pilot_module": scope.get("pilot_module"),
        "legacy_visibility": legacy.get("visibility"),
        "legacy_gate": legacy.get("default_current_gate_behavior"),
        "legacy_runtime_dependency_allowed": legacy.get("current_runtime_dependency_allowed"),
    }


def ready_rows(queue: dict[str, Any]) -> list[dict[str, Any]]:
    rows = queue.get("prompt_queue")
    if not isinstance(rows, list):
        raise H9Error("prompt_queue must be list")
    ready = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        execution = row.get("module_execution")
        if isinstance(execution, dict) and execution.get("status") == READY:
            ready.append(row)
    ready.sort(
        key=lambda row: (
            int(row.get("sequence") or 0),
            str(row.get("prompt_id") or ""),
        )
    )
    return ready


def unresolved_rows(queue: dict[str, Any]) -> list[dict[str, Any]]:
    rows = queue.get("prompt_queue")
    if not isinstance(rows, list):
        raise H9Error("prompt_queue must be list")

    unresolved: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue

        execution = row.get("module_execution")
        review = row.get("blueprint_review")
        row_status = row.get("status")
        execution_status = execution.get("status") if isinstance(execution, dict) else None
        review_status = review.get("status") if isinstance(review, dict) else None

        if "superseded" in {row_status, execution_status, review_status}:
            continue
        if review_status != "accepted_by_blueprint":
            unresolved.append(row)

    unresolved.sort(
        key=lambda row: (
            int(row.get("sequence") or 0),
            str(row.get("prompt_id") or ""),
        )
    )
    return unresolved


def wip_report(queue: dict[str, Any]) -> dict[str, Any]:
    unresolved = unresolved_rows(queue)
    return {
        "state": "WIP_OK" if len(unresolved) <= 1 else "WIP_LIMIT_VIOLATION",
        "unresolved_count": len(unresolved),
        "unresolved_prompt_ids": [str(row.get("prompt_id")) for row in unresolved],
    }


def notification(queue: dict[str, Any]) -> dict[str, Any]:
    ready = ready_rows(queue)
    state = (
        "NO_READY_PROMPT"
        if not ready
        else "READY_PROMPT"
        if len(ready) == 1
        else "MULTIPLE_READY_PROMPTS"
    )
    return {
        "state": state,
        "ready_count": len(ready),
        "ready_prompt_ids": [str(row.get("prompt_id")) for row in ready],
        "ready": ready,
    }


def sync(module_root: Path, blueprint_root: Path, module_id: str) -> list[str]:
    release_src = blueprint_root / "coordination/releases/current.yaml"
    queue_src = blueprint_root / "coordination/outgoing_prompts" / module_id / "index.yaml"
    release = load_yaml(release_src)
    queue = load_yaml(queue_src)
    if queue.get("schema_version") != "prompt_queue_v0_2":
        raise H9Error("Prompt Queue must use prompt_queue_v0_2")
    if queue.get("module") != module_id:
        raise H9Error("Prompt Queue module mismatch")

    snapshot = module_root / "coordination/blueprint_snapshot"
    changed: list[str] = []

    for src, dst in (
        (release_src, snapshot / "current_release.yaml"),
        (queue_src, snapshot / "prompt_queue.yaml"),
    ):
        if write_bytes_if_changed(dst, src.read_bytes()):
            changed.append(dst.relative_to(module_root).as_posix())

    prompt_root = queue_src.parent
    managed: set[Path] = set()
    for row in queue.get("prompt_queue", []):
        if not isinstance(row, dict):
            continue
        value = row.get("file")
        if not isinstance(value, str) or not value:
            continue
        rel = Path(value)
        if rel.is_absolute() or ".." in rel.parts:
            raise H9Error(f"unsafe prompt path: {value}")
        src = prompt_root / rel
        if not src.is_file():
            raise H9Error(f"referenced prompt is missing: {src}")
        dst = snapshot / "prompts" / rel
        managed.add(dst)
        if write_bytes_if_changed(dst, src.read_bytes()):
            changed.append(dst.relative_to(module_root).as_posix())

    managed_root = snapshot / "prompts"
    if managed_root.is_dir():
        for path in sorted(managed_root.rglob("*")):
            if path.is_file() and path not in managed:
                path.unlink()
                changed.append(path.relative_to(module_root).as_posix())

    state = {
        "schema_version": "module_blueprint_snapshot_state_v0_1",
        "module_id": module_id,
        "blueprint": {
            "branch": git(blueprint_root, "branch", "--show-current"),
            "head": git(blueprint_root, "rev-parse", "HEAD"),
        },
        "sources": {
            "release_path": "coordination/releases/current.yaml",
            "release_sha256": sha(release_src),
            "prompt_queue_path": (f"coordination/outgoing_prompts/{module_id}/index.yaml"),
            "prompt_queue_sha256": sha(queue_src),
        },
        "release": release_summary(release),
        "boundaries": {
            "network_used": False,
            "blueprint_repository_write_performed": False,
            "module_write_scope": "coordination/blueprint_snapshot",
            "prompt_claim_created": False,
            "operator_decision_created": False,
        },
    }
    state_path = snapshot / "sync_state.yaml"
    if write_yaml_if_changed(state_path, state):
        changed.append(state_path.relative_to(module_root).as_posix())
    return sorted(changed)


def snapshot_queue(module_root: Path) -> dict[str, Any]:
    return load_yaml(module_root / "coordination/blueprint_snapshot/prompt_queue.yaml")


def render_prompt(module_root: Path, *, read: bool) -> tuple[int, str]:
    queue = snapshot_queue(module_root)
    report = notification(queue)
    wip = wip_report(queue)
    lines = [
        f"state: {report['state']}",
        f"ready_count: {report['ready_count']}",
        f"wip_state: {wip['state']}",
        f"unresolved_count: {wip['unresolved_count']}",
    ]
    if wip["state"] == "WIP_LIMIT_VIOLATION":
        lines.append("unresolved_prompt_ids: " + ",".join(wip["unresolved_prompt_ids"]))
        lines.append("result: BLOCKED")
        return 2, "\n".join(lines)
    if report["state"] == "MULTIPLE_READY_PROMPTS":
        lines.append("ready_prompt_ids: " + ",".join(report["ready_prompt_ids"]))
        lines.append("result: BLOCKED")
        return 2, "\n".join(lines)
    if report["state"] == "NO_READY_PROMPT":
        lines.extend(["ready_prompt_ids: -", "result: ADVISORY"])
        return 0, "\n".join(lines)

    row = report["ready"][0]
    lines.extend(
        [
            f"prompt_id: {row.get('prompt_id')}",
            f"sequence: {row.get('sequence')}",
            f"priority: {row.get('priority')}",
            f"file: {row.get('file')}",
            "prompt_claim_created: false",
        ]
    )
    if read:
        rel = Path(str(row.get("file")))
        path = module_root / "coordination/blueprint_snapshot/prompts" / rel
        if not path.is_file():
            raise H9Error(f"prompt snapshot missing: {path}")
        lines.extend(["", "=" * 80, path.read_text(encoding="utf-8").rstrip()])
    return 0, "\n".join(lines)


def validate(module_root: Path, module_id: str) -> list[str]:
    errors: list[str] = []
    required = (
        "forprint_module_manifest.yaml",
        "coordination/status/current_status.yaml",
        "coordination/status/current_status.md",
        "coordination/status/next_questions_for_blueprint.md",
        "coordination/prompts/index.yaml",
        "coordination/reports/index.yaml",
    )
    for rel in required:
        if not (module_root / rel).is_file():
            errors.append(f"missing required file: {rel}")

    for rel in (
        "forprint_module_manifest.yaml",
        "coordination/status/current_status.yaml",
        "coordination/prompts/index.yaml",
        "coordination/reports/index.yaml",
    ):
        path = module_root / rel
        if not path.is_file():
            continue
        try:
            data = load_yaml(path)
        except Exception as exc:
            errors.append(str(exc))
            continue
        if data.get("module_id") != module_id:
            errors.append(f"module_id mismatch: {rel}")

    active = module_root / "coordination/prompts/active"
    if active.is_dir() and len(list(active.glob("*.md"))) > 1:
        errors.append("WIP=1 violation: multiple active prompt files")

    queue_path = module_root / "coordination/blueprint_snapshot/prompt_queue.yaml"
    if queue_path.is_file():
        wip = wip_report(load_yaml(queue_path))
        if wip["state"] == "WIP_LIMIT_VIOLATION":
            errors.append(
                "WIP=1 violation: unresolved Prompt Queue records: "
                + ",".join(wip["unresolved_prompt_ids"])
            )

    makefile = (module_root / "Makefile").read_text(encoding="utf-8")
    for target in (
        "module-start",
        "module-sync",
        "module-status",
        "module-validate",
        "coordination-sync-check",
        "blueprint-check",
        "blueprint-prompts-list",
        "prompt-notify",
        "prompt-next",
        "prompt-read-next",
        "check",
        "governance-check",
        "git-status",
    ):
        if f"\n{target}:\n" not in "\n" + makefile:
            errors.append(f"missing canonical Make target: {target}")
    return errors


def status(module_root: Path, module_id: str) -> str:
    current = load_yaml(module_root / "coordination/status/current_status.yaml")
    if current.get("module_id") != module_id:
        raise H9Error("current status module mismatch")

    state_path = module_root / "coordination/blueprint_snapshot/sync_state.yaml"
    queue_path = module_root / "coordination/blueprint_snapshot/prompt_queue.yaml"
    lines = [
        "ForPrint Logistics module status",
        f"module_id: {module_id}",
        f"branch: {git(module_root, 'branch', '--show-current')}",
        f"head: {git(module_root, 'rev-parse', 'HEAD')}",
        f"business_status: {current.get('status')}",
        f"business_phase: {current.get('phase')}",
    ]
    if state_path.is_file():
        state = load_yaml(state_path)
        release = state.get("release", {})
        lines.extend(
            [
                "",
                "CURRENT RELEASE AUTHORITY",
                f"base_release: {release.get('base_release')}",
                (f"base_release_state: {release.get('base_release_state')}"),
                (f"hardening_release: {release.get('hardening_release')}"),
                (f"hardening_state: {release.get('hardening_state')}"),
                f"pilot_module: {release.get('pilot_module')}",
                (f"legacy_compatibility_visibility: {release.get('legacy_visibility')}"),
                (f"legacy_compatibility_default_gate: {release.get('legacy_gate')}"),
            ]
        )
    else:
        lines.extend(["", "CURRENT RELEASE AUTHORITY", "snapshot: unavailable"])
    if queue_path.is_file():
        queue = load_yaml(queue_path)
        prompt = notification(queue)
        wip = wip_report(queue)
        lines.extend(
            [
                "",
                "PROMPT READINESS",
                f"state: {prompt['state']}",
                f"ready_count: {prompt['ready_count']}",
                f"wip_state: {wip['state']}",
                f"unresolved_count: {wip['unresolved_count']}",
            ]
        )
    lines.extend(
        [
            "",
            "BOUNDARIES",
            "network_used: false",
            "blueprint_repository_write_performed: false",
            "business_prompt_claim_created: false",
            "operator_decision_created: false",
        ]
    )
    return "\n".join(lines)


def awareness(module_root: Path) -> str:
    state = load_yaml(module_root / "coordination/blueprint_snapshot/sync_state.yaml")
    release = state.get("release", {})
    return "\n".join(
        [
            "ForPrint module document awareness",
            "result: PASSED",
            f"blueprint_head: {state.get('blueprint', {}).get('head')}",
            f"base_release: {release.get('base_release')}",
            (f"base_release_state: {release.get('base_release_state')}"),
            (f"hardening_release: {release.get('hardening_release')}"),
            (f"hardening_state: {release.get('hardening_state')}"),
            f"pilot_module: {release.get('pilot_module')}",
            "blueprint_repository_write_performed: false",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "sync",
            "awareness",
            "status",
            "prompt-next",
            "prompt-read-next",
            "coordination-validate",
        ),
    )
    parser.add_argument("--module-root", type=Path, required=True)
    parser.add_argument("--blueprint-root", type=Path)
    parser.add_argument("--module", required=True)
    args = parser.parse_args()
    root = args.module_root.resolve()

    try:
        if args.command == "sync":
            if args.blueprint_root is None:
                raise H9Error("--blueprint-root required")
            changed = sync(
                root,
                args.blueprint_root.resolve(),
                args.module,
            )
            print("ForPrint module sync")
            print("result: PASSED")
            print("network_used: false")
            print("blueprint_repository_write_performed: false")
            print("changed_paths: " + (",".join(changed) if changed else "-"))
            return 0
        if args.command == "awareness":
            print(awareness(root))
            return 0
        if args.command == "status":
            print(status(root, args.module))
            return 0
        if args.command in {"prompt-next", "prompt-read-next"}:
            code, text = render_prompt(
                root,
                read=args.command == "prompt-read-next",
            )
            print(text)
            return code
        errors = validate(root, args.module)
        print("ForPrint Logistics coordination validation")
        print(f"result: {'PASSED' if not errors else 'FAILED'}")
        print(f"errors: {len(errors)}")
        for error in errors:
            print(f"- {error}")
        print("network_used: false")
        print("blueprint_repository_write_performed: false")
        return 0 if not errors else 2
    except (H9Error, OSError, yaml.YAMLError) as exc:
        print(f"FAILED: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
