from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

import scripts.coordination.h9_runtime as runtime
import scripts.coordination_sync_check as sync_check


def write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, sort_keys=False),
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    ("statuses", "state"),
    [
        ([], "NO_READY_PROMPT"),
        (["prepared"], "NO_READY_PROMPT"),
        (["ready_for_module_pull"], "READY_PROMPT"),
        (
            ["ready_for_module_pull", "ready_for_module_pull"],
            "MULTIPLE_READY_PROMPTS",
        ),
    ],
)
def test_prompt_notification_states(
    tmp_path: Path,
    statuses: list[str],
    state: str,
) -> None:
    path = tmp_path / "coordination/outgoing_prompts/logistics_service/index.yaml"
    write_yaml(
        path,
        {
            "schema_version": "prompt_queue_v0_2",
            "module": "logistics_service",
            "prompt_queue": [
                {
                    "prompt_id": f"p{i}",
                    "sequence": i,
                    "file": f"approved/p{i}.md",
                    "module_execution": {"status": status},
                }
                for i, status in enumerate(statuses, start=1)
            ],
        },
    )
    result = sync_check.prompt_notification(
        tmp_path,
        "logistics_service",
    )
    assert result["state"] == state


@pytest.mark.parametrize(
    ("returncode", "stdout", "state"),
    [
        (0, "a" * 40 + "\trefs/heads/main\n", "CURRENT"),
        (0, "b" * 40 + "\trefs/heads/main\n", "STALE"),
        (1, "network down\n", "NETWORK_UNAVAILABLE"),
        (0, "", "REMOTE_BRANCH_NOT_FOUND"),
    ],
)
def test_four_freshness_states(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    returncode: int,
    stdout: str,
    state: str,
) -> None:
    def fake_require(root: Path, *args: str) -> str:
        del root
        return {
            ("rev-parse", "--is-inside-work-tree"): "true",
            ("rev-parse", "HEAD"): "a" * 40,
            ("branch", "--show-current"): "main",
            ("remote", "get-url", "origin"): "git@example/repo.git",
        }[args]

    monkeypatch.setattr(sync_check, "require_git", fake_require)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=[],
            returncode=returncode,
            stdout=stdout,
            stderr=None,
        ),
    )
    result = sync_check.remote_freshness(
        tmp_path,
        "origin",
        None,
    )
    assert result["state"] == state


def prepare_blueprint(root: Path) -> None:
    write_yaml(
        root / "coordination/releases/current.yaml",
        {
            "schema_version": "forprint_current_release_projection_v0_1",
            "release": {
                "base_release": "v0.4",
                "base_release_state": "PROMOTED_CLOSED_SEALED",
                "hardening_release": "v0.4.1",
                "hardening_state": "ACTIVE_CURRENT",
            },
            "legacy_compatibility": {
                "visibility": "advisory_yellow",
                "default_current_gate_behavior": ("nonblocking_excluded_or_skipped"),
                "current_runtime_dependency_allowed": False,
            },
            "module_scope": {"pilot_module": "logistics_service"},
        },
    )
    queue = root / "coordination/outgoing_prompts/logistics_service"
    write_yaml(
        queue / "index.yaml",
        {
            "schema_version": "prompt_queue_v0_2",
            "module": "logistics_service",
            "prompt_queue": [
                {
                    "prompt_id": "future",
                    "sequence": 1,
                    "priority": "normal",
                    "file": "drafts/future.md",
                    "module_execution": {"status": "prepared"},
                }
            ],
        },
    )
    prompt = queue / "drafts/future.md"
    prompt.parent.mkdir(parents=True, exist_ok=True)
    prompt.write_text("# Future\n", encoding="utf-8")


def test_module_sync_is_module_only_and_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = tmp_path / "module"
    blueprint = tmp_path / "blueprint"
    module.mkdir()
    blueprint.mkdir()
    prepare_blueprint(blueprint)
    before = {p.relative_to(blueprint): p.read_bytes() for p in blueprint.rglob("*") if p.is_file()}

    monkeypatch.setattr(
        runtime,
        "git",
        lambda root, *args: "audit/test" if args == ("branch", "--show-current") else "a" * 40,
    )
    first = runtime.sync(module, blueprint, "logistics_service")
    second = runtime.sync(module, blueprint, "logistics_service")
    after = {p.relative_to(blueprint): p.read_bytes() for p in blueprint.rglob("*") if p.is_file()}
    assert before == after
    assert first
    assert second == []

    state = runtime.load_yaml(module / "coordination/blueprint_snapshot/sync_state.yaml")
    assert state["release"]["base_release"] == "v0.4"
    assert state["release"]["base_release_state"] == "PROMOTED_CLOSED_SEALED"
    assert state["release"]["hardening_release"] == "v0.4.1"
    assert state["release"]["hardening_state"] == "ACTIVE_CURRENT"
    assert state["release"]["pilot_module"] == "logistics_service"
    assert state["boundaries"]["network_used"] is False
    assert state["boundaries"]["blueprint_repository_write_performed"] is False


def test_prompt_read_never_claims_and_multiple_fails_closed(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "coordination/blueprint_snapshot"
    write_yaml(
        snapshot / "prompt_queue.yaml",
        {
            "schema_version": "prompt_queue_v0_2",
            "module": "logistics_service",
            "prompt_queue": [
                {
                    "prompt_id": "one",
                    "sequence": 1,
                    "file": "approved/one.md",
                    "module_execution": {"status": "ready_for_module_pull"},
                }
            ],
        },
    )
    prompt = snapshot / "prompts/approved/one.md"
    prompt.parent.mkdir(parents=True, exist_ok=True)
    prompt.write_text("# One\n", encoding="utf-8")
    code, text = runtime.render_prompt(tmp_path, read=True)
    assert code == 0
    assert "prompt_claim_created: false" in text
    assert "CLAIMED" not in text

    queue = runtime.load_yaml(snapshot / "prompt_queue.yaml")
    queue["prompt_queue"].append(
        {
            "prompt_id": "two",
            "sequence": 2,
            "file": "approved/two.md",
            "module_execution": {"status": "ready_for_module_pull"},
        }
    )
    write_yaml(snapshot / "prompt_queue.yaml", queue)
    code, text = runtime.render_prompt(tmp_path, read=False)
    assert code == 2
    assert "MULTIPLE_READY_PROMPTS" in text


def test_status_exposes_release_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_yaml(
        tmp_path / "coordination/status/current_status.yaml",
        {
            "module_id": "logistics_service",
            "status": "completed_in_module",
            "phase": "tracking_events_v0_1",
        },
    )
    write_yaml(
        tmp_path / "coordination/blueprint_snapshot/sync_state.yaml",
        {
            "release": {
                "base_release": "v0.4",
                "base_release_state": "PROMOTED_CLOSED_SEALED",
                "hardening_release": "v0.4.1",
                "hardening_state": "ACTIVE_CURRENT",
                "pilot_module": "logistics_service",
                "legacy_visibility": "advisory_yellow",
                "legacy_gate": "nonblocking_excluded_or_skipped",
            }
        },
    )
    write_yaml(
        tmp_path / "coordination/blueprint_snapshot/prompt_queue.yaml",
        {
            "schema_version": "prompt_queue_v0_2",
            "module": "logistics_service",
            "prompt_queue": [],
        },
    )
    monkeypatch.setattr(
        runtime,
        "git",
        lambda root, *args: "feature/test" if args == ("branch", "--show-current") else "b" * 40,
    )
    text = runtime.status(tmp_path, "logistics_service")
    assert "base_release: v0.4" in text
    assert "base_release_state: PROMOTED_CLOSED_SEALED" in text
    assert "hardening_release: v0.4.1" in text
    assert "hardening_state: ACTIVE_CURRENT" in text
    assert "pilot_module: logistics_service" in text
    assert "state: NO_READY_PROMPT" in text


def test_wip_one_allows_single_completed_pending_review() -> None:
    queue = {
        "schema_version": "prompt_queue_v0_2",
        "module": "logistics_service",
        "prompt_queue": [
            {
                "prompt_id": "completed_pending",
                "sequence": 1,
                "module_execution": {"status": "completed_by_module"},
                "blueprint_review": {"status": "not_started"},
            }
        ],
    }
    report = runtime.wip_report(queue)
    assert report["state"] == "WIP_OK"
    assert report["unresolved_count"] == 1


def test_wip_one_blocks_ready_prompt_while_prior_work_is_unaccepted(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "coordination/blueprint_snapshot"
    write_yaml(
        snapshot / "prompt_queue.yaml",
        {
            "schema_version": "prompt_queue_v0_2",
            "module": "logistics_service",
            "prompt_queue": [
                {
                    "prompt_id": "completed_pending",
                    "sequence": 1,
                    "file": "completed/completed_pending.md",
                    "module_execution": {"status": "completed_by_module"},
                    "blueprint_review": {"status": "not_started"},
                },
                {
                    "prompt_id": "next_ready",
                    "sequence": 2,
                    "file": "approved/next_ready.md",
                    "module_execution": {"status": "ready_for_module_pull"},
                    "blueprint_review": {"status": "not_started"},
                },
            ],
        },
    )
    prompt = snapshot / "prompts/approved/next_ready.md"
    prompt.parent.mkdir(parents=True, exist_ok=True)
    prompt.write_text("# Next ready\\n", encoding="utf-8")

    code, text = runtime.render_prompt(tmp_path, read=True)
    assert code == 2
    assert "state: READY_PROMPT" in text
    assert "wip_state: WIP_LIMIT_VIOLATION" in text
    assert "unresolved_count: 2" in text
    assert "result: BLOCKED" in text
    assert "# Next ready" not in text


def test_wip_one_ignores_superseded_records() -> None:
    queue = {
        "schema_version": "prompt_queue_v0_2",
        "module": "logistics_service",
        "prompt_queue": [
            {
                "prompt_id": "old",
                "sequence": 1,
                "module_execution": {"status": "superseded"},
                "blueprint_review": {"status": "not_started"},
            },
            {
                "prompt_id": "current",
                "sequence": 2,
                "module_execution": {"status": "ready_for_module_pull"},
                "blueprint_review": {"status": "not_started"},
            },
        ],
    }
    report = runtime.wip_report(queue)
    assert report["state"] == "WIP_OK"
    assert report["unresolved_prompt_ids"] == ["current"]
