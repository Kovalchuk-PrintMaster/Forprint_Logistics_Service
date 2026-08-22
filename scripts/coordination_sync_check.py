from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

import yaml

QUEUE_SCHEMA = "prompt_queue_v0_2"
READY_STATUS = "ready_for_module_pull"


class SyncCheckError(RuntimeError):
    pass


def run_git(
    cwd: Path,
    *args: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def require_git(
    cwd: Path,
    *args: str,
) -> str:
    result = run_git(cwd, *args)
    if result.returncode != 0:
        raise SyncCheckError(f"git {' '.join(args)} failed: {result.stdout.strip()}")
    return result.stdout.strip()


def load_queue(
    blueprint_root: Path,
    module_id: str,
) -> tuple[Path, dict[str, Any]]:
    path = blueprint_root / "coordination/outgoing_prompts" / module_id / "index.yaml"
    if not path.is_file():
        raise SyncCheckError(f"prompt queue is missing: {path}")

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise SyncCheckError(f"prompt queue YAML is invalid: {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise SyncCheckError(f"prompt queue must be a mapping: {path}")
    if data.get("schema_version") != QUEUE_SCHEMA:
        raise SyncCheckError(f"prompt queue must use {QUEUE_SCHEMA}: {path}")
    if data.get("module") != module_id:
        raise SyncCheckError(f"prompt queue module mismatch: expected {module_id!r}")

    rows = data.get("prompt_queue")
    if not isinstance(rows, list):
        raise SyncCheckError("prompt_queue must be a list")
    return path, data


def prompt_notification(
    blueprint_root: Path,
    module_id: str,
) -> dict[str, Any]:
    path, data = load_queue(blueprint_root, module_id)
    ready: list[dict[str, Any]] = []

    for row in data["prompt_queue"]:
        if not isinstance(row, dict):
            continue
        execution = row.get("module_execution")
        if not isinstance(execution, dict):
            continue
        if execution.get("status") == READY_STATUS:
            ready.append(row)

    ready.sort(
        key=lambda item: (
            int(item.get("sequence") or 0),
            str(item.get("prompt_id") or ""),
        )
    )

    if len(ready) == 0:
        state = "NO_READY_PROMPT"
    elif len(ready) == 1:
        state = "READY_PROMPT"
    else:
        state = "MULTIPLE_READY_PROMPTS"

    return {
        "state": state,
        "queue_path": str(path),
        "ready_count": len(ready),
        "ready_prompt_ids": [str(item.get("prompt_id")) for item in ready],
        "ready_prompt": (
            {
                "prompt_id": ready[0].get("prompt_id"),
                "sequence": ready[0].get("sequence"),
                "priority": ready[0].get("priority"),
                "file": ready[0].get("file"),
            }
            if len(ready) == 1
            else None
        ),
    }


def remote_freshness(
    blueprint_root: Path,
    remote: str,
    branch: str | None,
) -> dict[str, Any]:
    if not blueprint_root.is_dir():
        raise SyncCheckError(f"Blueprint root does not exist: {blueprint_root}")

    inside = require_git(
        blueprint_root,
        "rev-parse",
        "--is-inside-work-tree",
    )
    if inside != "true":
        raise SyncCheckError("Blueprint root is not a Git worktree")

    local_head = require_git(
        blueprint_root,
        "rev-parse",
        "HEAD",
    )
    local_branch = branch or require_git(
        blueprint_root,
        "branch",
        "--show-current",
    )
    if not local_branch:
        raise SyncCheckError("Blueprint checkout is detached; explicit --branch required")

    remote_url = require_git(
        blueprint_root,
        "remote",
        "get-url",
        remote,
    )

    remote_result = subprocess.run(
        [
            "git",
            "ls-remote",
            "--heads",
            remote_url,
            f"refs/heads/{local_branch}",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if remote_result.returncode != 0:
        return {
            "state": "NETWORK_UNAVAILABLE",
            "local_head": local_head,
            "branch": local_branch,
            "remote": remote,
            "remote_url": remote_url,
            "remote_head": None,
            "detail": remote_result.stdout.strip(),
        }

    lines = [line for line in remote_result.stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        return {
            "state": "REMOTE_BRANCH_NOT_FOUND",
            "local_head": local_head,
            "branch": local_branch,
            "remote": remote,
            "remote_url": remote_url,
            "remote_head": None,
            "detail": (f"expected one remote branch match, got {len(lines)}"),
        }

    remote_head = lines[0].split()[0]
    state = "CURRENT" if local_head == remote_head else "STALE"

    return {
        "state": state,
        "local_head": local_head,
        "branch": local_branch,
        "remote": remote,
        "remote_url": remote_url,
        "remote_head": remote_head,
        "detail": None,
    }


def build_report(
    blueprint_root: Path,
    module_id: str,
    *,
    remote: str,
    branch: str | None,
    network: bool,
) -> dict[str, Any]:
    prompt = prompt_notification(
        blueprint_root,
        module_id,
    )
    freshness: dict[str, Any] | None = None

    if network:
        freshness = remote_freshness(
            blueprint_root,
            remote,
            branch,
        )

    errors: list[str] = []
    advisories: list[str] = []

    if freshness is not None:
        if freshness["state"] == "STALE":
            errors.append("BLUEPRINT_CHECKOUT_STALE")
        elif freshness["state"] == "NETWORK_UNAVAILABLE":
            errors.append("BLUEPRINT_REMOTE_UNAVAILABLE")
        elif freshness["state"] == "REMOTE_BRANCH_NOT_FOUND":
            errors.append("BLUEPRINT_REMOTE_BRANCH_NOT_FOUND")

    if prompt["state"] == "MULTIPLE_READY_PROMPTS":
        errors.append("MULTIPLE_READY_PROMPTS")
    elif prompt["state"] == "NO_READY_PROMPT":
        advisories.append("NO_READY_PROMPT")

    if errors:
        result_state = "BLOCKED"
    elif advisories:
        result_state = "ADVISORY"
    else:
        result_state = "READY"

    return {
        "schema_version": "module_coordination_sync_check_v0_1",
        "mode": ("network_read_only" if network else "local_read_only"),
        "result_state": result_state,
        "module_id": module_id,
        "blueprint_root": str(blueprint_root.resolve()),
        "freshness": freshness,
        "prompt_notification": prompt,
        "errors": errors,
        "advisories": advisories,
        "boundaries": {
            "blueprint_repository_write_performed": False,
            "module_repository_write_performed": False,
            "git_fetch_performed": False,
            "git_pull_performed": False,
            "git_remote_tracking_ref_updated": False,
            "prompt_claim_created": False,
            "queue_mutated": False,
            "operator_decision_created": False,
        },
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        "ForPrint Coordination Sync Check v0.1",
        f"result_state: {report['result_state']}",
        f"mode: {report['mode']}",
        f"module: {report['module_id']}",
    ]

    freshness = report.get("freshness")
    if isinstance(freshness, dict):
        lines.extend(
            [
                "",
                "BLUEPRINT FRESHNESS",
                f"state: {freshness.get('state')}",
                f"branch: {freshness.get('branch')}",
                f"local_head: {freshness.get('local_head')}",
                f"remote_head: {freshness.get('remote_head')}",
            ]
        )

    prompt = report["prompt_notification"]
    lines.extend(
        [
            "",
            "PROMPT NOTIFICATION",
            f"state: {prompt['state']}",
            f"ready_count: {prompt['ready_count']}",
            (
                "ready_prompt_ids: "
                + (",".join(prompt["ready_prompt_ids"]) if prompt["ready_prompt_ids"] else "-")
            ),
            "",
            "ERRORS",
            ",".join(report["errors"]) if report["errors"] else "-",
            "",
            "ADVISORIES",
            (",".join(report["advisories"]) if report["advisories"] else "-"),
            "",
            "BOUNDARIES",
            "blueprint_repository_write_performed: false",
            "module_repository_write_performed: false",
            "git_fetch_performed: false",
            "git_pull_performed: false",
            "prompt_claim_created: false",
            "queue_mutated: false",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blueprint-root", type=Path, required=True)
    parser.add_argument("--module", required=True)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--branch")
    parser.add_argument(
        "--local-only",
        action="store_true",
    )
    parser.add_argument(
        "--output-format",
        choices=("text", "yaml", "json"),
        default="text",
    )
    args = parser.parse_args()

    try:
        report = build_report(
            args.blueprint_root.resolve(),
            args.module,
            remote=args.remote,
            branch=args.branch,
            network=not args.local_only,
        )
    except SyncCheckError as exc:
        print(f"FAILED: {exc}")
        return 2

    if args.output_format == "yaml":
        print(
            yaml.safe_dump(
                report,
                sort_keys=False,
                allow_unicode=True,
            ).rstrip()
        )
    elif args.output_format == "json":
        print(
            json.dumps(
                report,
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    else:
        print(render_text(report))

    return 0 if report["result_state"] in {"READY", "ADVISORY"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
