#!/usr/bin/env python3
"""Validate hardened Tracking Events Completion Exchange v0.3 reference evidence."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]

SCHEMA = "module_completion_packet_v0_3"
PROTOCOL = "blueprint_completion_intake_v0_3"
CONTRACT_ID = "logistics_service_tracking_events_v0_1_contract_v0_3"
PROMPT_ID = "logistics_service_tracking_events_v0_1"
PROMPT_HASH = "8158ff1feb9c2416aac97f70ce20110de3195d5239a343be940705d096242094"
BASE = "4812047963427043d616871075ac807a35e51aff"
TIP = "bbc298e294bd9e7e6cca976d4a8077c52c4a51ff"

EXPECTED_CHECKS = {
    "TRK-CHECK-001": "make tracking-events-check",
    "TRK-CHECK-002": "make governance-check",
    "TRK-CHECK-003": "make coordination-check",
    "TRK-CHECK-004": "make check",
    "TRK-CHECK-005": "make check-report",
    "TRK-CHECK-006": "make check-report-full",
    "TRK-CHECK-007": "make module-validate",
    "TRK-CHECK-008": "git diff --check",
    "TRK-CHECK-009": "git status --short",
}

REQUIREMENT_POLICIES = {
    "TRK-REQ-001": "paths_and_tests",
    "TRK-REQ-002": "paths_and_tests",
    "TRK-REQ-003": "paths_and_tests",
    "TRK-REQ-004": "paths_and_tests",
    "TRK-REQ-005": "paths_and_tests",
    "TRK-REQ-006": "paths_and_tests",
    "TRK-REQ-007": "paths_and_tests",
    "TRK-REQ-008": "artifacts",
    "TRK-REQ-009": "paths_and_tests",
    "TRK-REQ-010": "boundary",
}

DECLARED_PATHS = {
    "Makefile",
    (
        "coordination/completion_packets/records/"
        "2026-08-12__logistics_service__tracking_events_v0_1_"
        "completion_superseding_v0_3_reference.yaml"
    ),
    (
        "coordination/reports/completion/"
        "2026-08-12__logistics_service__tracking_events_v0_1_"
        "completion_superseding_v0_3_reference.md"
    ),
    "docs/development/coordination/completion_reporting_protocol.md",
    ("scripts/coordination/validate_tracking_events_v0_3_reference_completion.py"),
    ("tests/coordination/test_tracking_events_v0_3_reference_completion.py"),
}

BOUNDARY_FLAGS = {
    "no_production_api",
    "no_live_external_integrations",
    "no_real_1c_sync",
    "no_production_write",
    "no_automatic_posting",
    "no_provider_calls",
    "no_telegram_api_calls",
    "no_cross_repository_writes",
    "no_database_implementation",
}

SUPERSEDES_ID = "logistics_service_tracking_events_v0_1_completed_v0_2"
SUPERSEDES_PATH = (
    "coordination/completion_packets/records/"
    "2026-08-07__logistics_service__tracking_events_v0_1_"
    "completion_superseding_v0_2.yaml"
)

SHA256 = re.compile(r"^[0-9a-f]{64}$")
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


class ValidationError(ValueError):
    pass


def _run_git(
    repo: Path,
    *args: str,
    env: dict[str, str] | None = None,
    allowed: tuple[int, ...] = (0,),
) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        env=env,
        capture_output=True,
        check=False,
    )
    if result.returncode not in allowed:
        detail = (
            result.stderr.decode("utf-8", errors="replace").strip()
            or result.stdout.decode("utf-8", errors="replace").strip()
        )
        raise ValidationError(f"git {' '.join(args)} failed ({result.returncode}): {detail}")
    return result


def _git_text(repo: Path, *args: str) -> str:
    return _run_git(repo, *args).stdout.decode("utf-8", errors="replace").rstrip("\n")


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dirty_paths(repo: Path) -> set[str]:
    paths: set[str] = set()
    for args in (
        ("diff", "--name-only"),
        ("diff", "--cached", "--name-only"),
        ("ls-files", "--others", "--exclude-standard"),
    ):
        paths.update(line for line in _git_text(repo, *args).splitlines() if line)
    return paths


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ValidationError(f"invalid YAML {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValidationError(f"YAML root must be mapping: {path}")
    return value


def _exists_at(repo: Path, commit: str, relative: str) -> bool:
    return (
        _run_git(
            repo,
            "cat-file",
            "-e",
            f"{commit}:{relative}",
            allowed=(0, 1),
        ).returncode
        == 0
    )


def _commit_exists(repo: Path, commit: str) -> bool:
    return (
        _run_git(
            repo,
            "cat-file",
            "-e",
            f"{commit}^{{commit}}",
            allowed=(0, 1),
        ).returncode
        == 0
    )


def _changed_paths(repo: Path, base: str, tip: str) -> set[str]:
    return {line for line in _git_text(repo, "diff", "--name-only", base, tip).splitlines() if line}


def _validate_timestamp(value: Any, *, check_id: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{check_id} executed_at is required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValidationError(f"{check_id} executed_at is not valid ISO-8601") from error
    if parsed.tzinfo is None:
        raise ValidationError(f"{check_id} executed_at must include timezone information")


def validate_check_results(
    packet: dict[str, Any],
    *,
    repo: Path | None = None,
    declared_paths: set[str] | None = None,
) -> None:
    raw = packet.get("check_results")
    if not isinstance(raw, list):
        raise ValidationError("check_results must be a list")

    by_id: dict[str, dict[str, Any]] = {}
    for item in raw:
        if not isinstance(item, dict):
            raise ValidationError("every check result must be a mapping")
        check_id = item.get("check_id")
        if not isinstance(check_id, str) or not check_id:
            raise ValidationError("check_id must be a non-empty string")
        if check_id in by_id:
            raise ValidationError(f"duplicate check_id: {check_id}")
        by_id[check_id] = item

    if set(by_id) != set(EXPECTED_CHECKS):
        missing = sorted(set(EXPECTED_CHECKS) - set(by_id))
        unknown = sorted(set(by_id) - set(EXPECTED_CHECKS))
        raise ValidationError(
            f"required check coverage mismatch: missing={missing}, unknown={unknown}"
        )

    for check_id, expected_command in EXPECTED_CHECKS.items():
        item = by_id[check_id]
        if item.get("command") != expected_command:
            raise ValidationError(f"{check_id} command does not match contract")
        if item.get("status") != "passed":
            raise ValidationError(f"{check_id} status must be passed")
        exit_code = item.get("exit_code")
        if not isinstance(exit_code, int) or isinstance(exit_code, bool):
            raise ValidationError(f"{check_id} exit_code is required")
        if exit_code != 0:
            raise ValidationError(f"{check_id} exit_code must be zero")
        _validate_timestamp(item.get("executed_at"), check_id=check_id)

        evidence = item.get("execution_evidence")
        if not isinstance(evidence, dict):
            raise ValidationError(f"{check_id} execution_evidence is required")
        output_sha256 = evidence.get("output_sha256")
        if not isinstance(output_sha256, str) or SHA256.fullmatch(output_sha256) is None:
            raise ValidationError(f"{check_id} execution_evidence.output_sha256 is invalid")

    status_result = by_id["TRK-CHECK-009"]
    expectation = status_result.get("expectation")
    observation = status_result.get("observation")
    if not isinstance(expectation, dict) or not isinstance(observation, dict):
        raise ValidationError("TRK-CHECK-009 requires expectation and observation mappings")
    if expectation.get("type") != "exact_declared_dirty_path_set":
        raise ValidationError("TRK-CHECK-009 expectation type is invalid")

    allowed = expectation.get("allowed_paths")
    actual = observation.get("actual_paths")
    unexpected = observation.get("unexpected_paths")
    missing = observation.get("missing_expected_paths")
    if not all(isinstance(value, list) for value in (allowed, actual, unexpected, missing)):
        raise ValidationError("TRK-CHECK-009 path-set fields must all be lists")

    expected_set = set(declared_paths or DECLARED_PATHS)
    if set(allowed) != expected_set:
        raise ValidationError("TRK-CHECK-009 allowed_paths differ from declared mutation set")
    if set(actual) != expected_set:
        raise ValidationError("TRK-CHECK-009 observation actual_paths differ from declared set")
    if unexpected:
        raise ValidationError(f"TRK-CHECK-009 unexpected paths are present: {unexpected}")
    if missing:
        raise ValidationError(f"TRK-CHECK-009 expected paths are missing: {missing}")

    if repo is not None:
        current = _dirty_paths(repo)
        if current != expected_set:
            raise ValidationError(
                "current worktree dirty path set differs from declared set: "
                f"actual={sorted(current)}, expected={sorted(expected_set)}"
            )


def validate_precommit_surface(
    repo: Path,
    declared_paths: set[str],
) -> dict[str, Any]:
    repo = repo.resolve()
    declared = set(declared_paths)

    staged_before = {
        line for line in _git_text(repo, "diff", "--cached", "--name-only").splitlines() if line
    }
    if staged_before:
        raise ValidationError("real Git index is pre-staged: " + ", ".join(sorted(staged_before)))

    dirty_before = _dirty_paths(repo)
    unexpected = sorted(dirty_before - declared)
    missing = sorted(declared - dirty_before)
    if unexpected:
        raise ValidationError("unexpected dirty paths: " + ", ".join(unexpected))
    if missing:
        raise ValidationError("declared expected paths are not dirty: " + ", ".join(missing))

    status_before = _run_git(
        repo,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    ).stdout

    index_rel = _git_text(repo, "rev-parse", "--git-path", "index")
    index_path = Path(index_rel)
    if not index_path.is_absolute():
        index_path = repo / index_path
    index_hash_before = _file_sha256(index_path) if index_path.exists() else None

    with tempfile.TemporaryDirectory(prefix="logistics-v03-precommit-") as temporary_directory:
        temporary_index = Path(temporary_directory) / "index"
        environment = os.environ.copy()
        environment["GIT_INDEX_FILE"] = str(temporary_index)

        _run_git(repo, "read-tree", "HEAD", env=environment)
        _run_git(
            repo,
            "add",
            "-A",
            "--",
            *sorted(declared),
            env=environment,
        )

        temporary_staged = {
            line
            for line in _run_git(
                repo,
                "diff",
                "--cached",
                "--name-only",
                env=environment,
            )
            .stdout.decode("utf-8", errors="replace")
            .splitlines()
            if line
        }
        if temporary_staged != declared:
            raise ValidationError(
                "temporary staged path set differs from declared set: "
                f"actual={sorted(temporary_staged)}, "
                f"expected={sorted(declared)}"
            )

        diff_check = _run_git(
            repo,
            "diff",
            "--cached",
            "--check",
            "--",
            *sorted(declared),
            env=environment,
            allowed=(0, 2),
        )
        if diff_check.returncode != 0:
            detail = (
                diff_check.stdout.decode("utf-8", errors="replace")
                + diff_check.stderr.decode("utf-8", errors="replace")
            ).strip()
            raise ValidationError(
                "temporary-index diff check failed" + (f": {detail}" if detail else "")
            )

    staged_after = {
        line for line in _git_text(repo, "diff", "--cached", "--name-only").splitlines() if line
    }
    if staged_after:
        raise ValidationError("temporary-index validation mutated the real staged path set")

    index_hash_after = _file_sha256(index_path) if index_path.exists() else None
    if index_hash_after != index_hash_before:
        raise ValidationError("temporary-index validation changed real Git index bytes")

    status_after = _run_git(
        repo,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    ).stdout
    if status_after != status_before:
        raise ValidationError("temporary-index validation changed worktree status")

    return {
        "status": "passed",
        "validator": "temporary_git_index",
        "declared_paths": sorted(declared),
        "unexpected_paths": [],
        "missing_expected_paths": [],
        "temporary_staged_paths": sorted(temporary_staged),
        "temporary_index_diff_check": "passed",
        "real_git_index_changed": False,
        "worktree_changed": False,
    }


def _frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValidationError("completion report must start with YAML frontmatter")
    closing = text.find("\n---\n", 4)
    if closing < 0:
        raise ValidationError("completion report frontmatter is not closed")
    value = yaml.safe_load(text[4:closing])
    if not isinstance(value, dict):
        raise ValidationError("completion report frontmatter must be a mapping")
    return value


def validate_packet(
    packet_path: Path,
    *,
    repo: Path = ROOT,
    run_precommit: bool = True,
) -> dict[str, Any]:
    packet = _load_yaml(packet_path)

    if packet.get("schema_version") != SCHEMA:
        raise ValidationError("packet schema mismatch")
    if packet.get("protocol_version") != PROTOCOL:
        raise ValidationError("packet protocol mismatch")
    if packet.get("module_id") != "logistics_service":
        raise ValidationError("module_id mismatch")
    if packet.get("phase") != "tracking_events_v0_1":
        raise ValidationError("phase mismatch")
    if packet.get("prompt_id") != PROMPT_ID:
        raise ValidationError("prompt_id mismatch")

    prompt_contract = packet.get("prompt_contract")
    if not isinstance(prompt_contract, dict):
        raise ValidationError("prompt_contract must be a mapping")
    expected_prompt_contract = {
        "contract_id": CONTRACT_ID,
        "revision": "module_prompt_contract_v0_3",
        "source_prompt_sha256": PROMPT_HASH,
    }
    if prompt_contract != expected_prompt_contract:
        raise ValidationError("prompt contract binding mismatch")

    implementation_range = packet.get("implementation_range")
    if not isinstance(implementation_range, dict):
        raise ValidationError("implementation_range must be a mapping")
    base = implementation_range.get("base_commit")
    tip = implementation_range.get("tip_commit")
    if base != BASE or tip != TIP:
        raise ValidationError("implementation range mismatch")
    if (
        not isinstance(base, str)
        or FULL_SHA.fullmatch(base) is None
        or not isinstance(tip, str)
        or FULL_SHA.fullmatch(tip) is None
    ):
        raise ValidationError("implementation range SHA format invalid")
    if not _commit_exists(repo, BASE) or not _commit_exists(repo, TIP):
        raise ValidationError("implementation range commit missing locally")
    if (
        _run_git(
            repo,
            "merge-base",
            "--is-ancestor",
            BASE,
            TIP,
            allowed=(0, 1),
        ).returncode
        != 0
    ):
        raise ValidationError("implementation base is not ancestor of tip")

    changed = _changed_paths(repo, BASE, TIP)

    requirement_results = packet.get("requirement_results")
    if not isinstance(requirement_results, list):
        raise ValidationError("requirement_results must be a list")
    by_requirement: dict[str, dict[str, Any]] = {}
    for item in requirement_results:
        if not isinstance(item, dict):
            raise ValidationError("requirement result must be a mapping")
        requirement_id = item.get("requirement_id")
        if (
            not isinstance(requirement_id, str)
            or not requirement_id
            or requirement_id in by_requirement
        ):
            raise ValidationError("requirement IDs must be unique non-empty strings")
        by_requirement[requirement_id] = item

    if set(by_requirement) != set(REQUIREMENT_POLICIES):
        raise ValidationError("requirement coverage must be exactly TRK-REQ-001..010")

    boundary = packet.get("boundary_confirmation")
    if not isinstance(boundary, dict):
        raise ValidationError("boundary_confirmation must be a mapping")
    if set(boundary) != BOUNDARY_FLAGS:
        raise ValidationError("boundary_confirmation must contain exactly the nine required flags")
    if any(boundary[flag] is not True for flag in BOUNDARY_FLAGS):
        raise ValidationError("all boundary confirmations must be true")

    for requirement_id, policy in REQUIREMENT_POLICIES.items():
        item = by_requirement[requirement_id]
        if item.get("status") != "completed":
            raise ValidationError(f"{requirement_id} must be completed")
        if policy == "paths_and_tests":
            implementation_paths = item.get("implementation_paths")
            test_paths = item.get("test_paths")
            if (
                not isinstance(implementation_paths, list)
                or not implementation_paths
                or not isinstance(test_paths, list)
                or not test_paths
            ):
                raise ValidationError(
                    f"{requirement_id} requires implementation_paths and test_paths"
                )
            evidence_paths = implementation_paths + test_paths
            for relative in evidence_paths:
                if (
                    not isinstance(relative, str)
                    or not relative
                    or not _exists_at(repo, TIP, relative)
                ):
                    raise ValidationError(f"{requirement_id} evidence missing at tip: {relative!r}")
            if not any(relative in changed for relative in evidence_paths):
                raise ValidationError(f"{requirement_id} lacks changed-path evidence")
        elif policy == "artifacts":
            artifact_paths = item.get("artifact_paths")
            if not isinstance(artifact_paths, list) or not artifact_paths:
                raise ValidationError(f"{requirement_id} requires artifact_paths")
            for relative in artifact_paths:
                if (
                    not isinstance(relative, str)
                    or not relative
                    or not _exists_at(repo, TIP, relative)
                ):
                    raise ValidationError(f"{requirement_id} artifact missing at tip: {relative!r}")

    validate_check_results(
        packet,
        repo=repo,
        declared_paths=set(DECLARED_PATHS),
    )

    if packet.get("supersedes_completion_id") != SUPERSEDES_ID:
        raise ValidationError("supersedes_completion_id mismatch")
    if packet.get("supersedes_packet_path") != SUPERSEDES_PATH:
        raise ValidationError("supersedes_packet_path mismatch")
    historical = _load_yaml(repo / SUPERSEDES_PATH)
    if historical.get("completion_id") != SUPERSEDES_ID:
        raise ValidationError("superseded packet completion_id mismatch")

    report_rel = packet.get("report_path")
    if not isinstance(report_rel, str):
        raise ValidationError("report_path missing")
    frontmatter = _frontmatter(repo / report_rel)
    expected_frontmatter = {
        "schema_version": SCHEMA,
        "protocol_version": PROTOCOL,
        "prompt_contract_id": CONTRACT_ID,
        "prompt_id": PROMPT_ID,
        "target_module": "logistics_service",
        "phase": "tracking_events_v0_1",
        "implementation_base_commit": BASE,
        "implementation_tip_commit": TIP,
    }
    for key, expected in expected_frontmatter.items():
        if frontmatter.get(key) != expected:
            raise ValidationError(f"completion report frontmatter mismatch: {key}")

    current_outputs = packet.get("current_outputs")
    if not isinstance(current_outputs, list) or not current_outputs:
        raise ValidationError("current_outputs must be a non-empty list")
    head = _git_text(repo, "rev-parse", "HEAD")
    for relative in current_outputs:
        if (
            not isinstance(relative, str)
            or relative.startswith("/")
            or ".." in Path(relative).parts
            or not _exists_at(repo, head, relative)
        ):
            raise ValidationError(f"current output is not committed at HEAD: {relative!r}")

    recorded_precommit = packet.get("precommit_surface_validation")
    if not isinstance(recorded_precommit, dict):
        raise ValidationError("precommit_surface_validation is required")

    required_precommit = {
        "status": "passed",
        "validator": "temporary_git_index",
        "declared_paths": sorted(DECLARED_PATHS),
        "unexpected_paths": [],
        "missing_expected_paths": [],
        "temporary_staged_paths": sorted(DECLARED_PATHS),
        "temporary_index_diff_check": "passed",
        "real_git_index_changed": False,
        "worktree_changed": False,
    }
    for key, expected in required_precommit.items():
        if recorded_precommit.get(key) != expected:
            raise ValidationError(f"precommit_surface_validation mismatch: {key}")

    actual_precommit = None
    if run_precommit:
        actual_precommit = validate_precommit_surface(repo, set(DECLARED_PATHS))

    return {
        "requirements": sorted(REQUIREMENT_POLICIES),
        "checks": sorted(EXPECTED_CHECKS),
        "precommit": actual_precommit or recorded_precommit,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet")
    args = parser.parse_args()
    try:
        result = validate_packet(ROOT / args.packet)
    except ValidationError as error:
        print(f"FAILED: {error}")
        print("RESULT: TRACKING_EVENTS_V03_REFERENCE_COMPLETION_INVALID")
        return 1

    print("Tracking Events v0.3 hardened reference completion validation")
    print(f"requirements: {len(result['requirements'])}/10")
    print(f"required checks: {len(result['checks'])}/9")
    print("temporary-index precommit: passed")
    print("real Git index changed: false")
    print("candidate reference only: true")
    print("Blueprint acceptance: false")
    print("RESULT: TRACKING_EVENTS_V03_REFERENCE_COMPLETION_HARDENED_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
