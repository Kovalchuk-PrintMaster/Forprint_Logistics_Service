from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from scripts.coordination import (
    validate_tracking_events_v0_3_reference_completion as validator,
)


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "user.email", "test@example.invalid")
    (repo / "tracked.txt").write_text("clean\n", encoding="utf-8")
    (repo / "other.txt").write_text("other\n", encoding="utf-8")
    git(repo, "add", "tracked.txt", "other.txt")
    git(repo, "commit", "-m", "baseline")
    return repo


def valid_check_results() -> list[dict]:
    return [
        {
            "check_id": check_id,
            "command": command,
            "status": "passed",
            "exit_code": 0,
            "executed_at": "2026-08-12T18:00:00+03:00",
            "execution_evidence": {
                "output_sha256": hashlib.sha256(f"{check_id}\n".encode()).hexdigest()
            },
        }
        for check_id, command in validator.EXPECTED_CHECKS.items()
    ]


def packet_with_checks() -> dict:
    results = valid_check_results()
    status = next(item for item in results if item["check_id"] == "TRK-CHECK-009")
    status["expectation"] = {
        "type": "exact_declared_dirty_path_set",
        "allowed_paths": ["tracked.txt"],
    }
    status["observation"] = {
        "actual_paths": ["tracked.txt"],
        "unexpected_paths": [],
        "missing_expected_paths": [],
    }
    return {"check_results": results}


def test_modified_tracked_file_passes(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
    assert validator.validate_precommit_surface(repo, {"tracked.txt"})["status"] == "passed"


def test_new_untracked_file_passes(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    (repo / "new.txt").write_text("new\n", encoding="utf-8")
    assert validator.validate_precommit_surface(repo, {"new.txt"})["status"] == "passed"


def test_new_untracked_trailing_whitespace_fails(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    (repo / "new.txt").write_text("bad   \n", encoding="utf-8")
    with pytest.raises(validator.ValidationError):
        validator.validate_precommit_surface(repo, {"new.txt"})


def test_modified_tracked_trailing_whitespace_fails(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    (repo / "tracked.txt").write_text("bad   \n", encoding="utf-8")
    with pytest.raises(validator.ValidationError):
        validator.validate_precommit_surface(repo, {"tracked.txt"})


def test_unexpected_dirty_path_fails(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
    (repo / "unexpected.txt").write_text("unexpected\n", encoding="utf-8")
    with pytest.raises(validator.ValidationError):
        validator.validate_precommit_surface(repo, {"tracked.txt"})


def test_declared_expected_path_missing_fails(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
    with pytest.raises(validator.ValidationError):
        validator.validate_precommit_surface(repo, {"tracked.txt", "other.txt"})


def test_real_git_index_prestaged_fails(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
    git(repo, "add", "tracked.txt")
    with pytest.raises(validator.ValidationError):
        validator.validate_precommit_surface(repo, {"tracked.txt"})


def test_temporary_index_does_not_mutate_real_index(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
    index = repo / ".git" / "index"
    before = hashlib.sha256(index.read_bytes()).hexdigest()
    validator.validate_precommit_surface(repo, {"tracked.txt"})
    after = hashlib.sha256(index.read_bytes()).hexdigest()
    assert before == after
    assert git(repo, "diff", "--cached", "--name-only") == ""


def test_git_status_actual_path_set_mismatch_fails(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
    packet = packet_with_checks()
    status = next(item for item in packet["check_results"] if item["check_id"] == "TRK-CHECK-009")
    status["observation"]["actual_paths"] = ["other.txt"]
    with pytest.raises(validator.ValidationError):
        validator.validate_check_results(
            packet,
            repo=repo,
            declared_paths={"tracked.txt"},
        )


def test_required_check_missing_exit_code_fails() -> None:
    packet = packet_with_checks()
    packet["check_results"][0].pop("exit_code")
    with pytest.raises(validator.ValidationError):
        validator.validate_check_results(packet, declared_paths={"tracked.txt"})


def test_required_check_nonzero_exit_code_fails() -> None:
    packet = packet_with_checks()
    packet["check_results"][0]["exit_code"] = 1
    with pytest.raises(validator.ValidationError):
        validator.validate_check_results(packet, declared_paths={"tracked.txt"})


def test_required_check_missing_output_sha_fails() -> None:
    packet = packet_with_checks()
    packet["check_results"][0]["execution_evidence"].pop("output_sha256")
    with pytest.raises(validator.ValidationError):
        validator.validate_check_results(packet, declared_paths={"tracked.txt"})


def test_required_check_command_mismatch_fails() -> None:
    packet = packet_with_checks()
    packet["check_results"][0]["command"] = "make wrong-command"
    with pytest.raises(validator.ValidationError):
        validator.validate_check_results(packet, declared_paths={"tracked.txt"})


def test_duplicate_check_id_fails() -> None:
    packet = packet_with_checks()
    packet["check_results"][1]["check_id"] = "TRK-CHECK-001"
    with pytest.raises(validator.ValidationError):
        validator.validate_check_results(packet, declared_paths={"tracked.txt"})


def test_missing_required_check_id_fails() -> None:
    packet = packet_with_checks()
    packet["check_results"] = packet["check_results"][:-1]
    with pytest.raises(validator.ValidationError):
        validator.validate_check_results(packet, declared_paths={"tracked.txt"})


def test_missing_executed_at_fails() -> None:
    packet = packet_with_checks()
    packet["check_results"][0].pop("executed_at")
    with pytest.raises(validator.ValidationError):
        validator.validate_check_results(packet, declared_paths={"tracked.txt"})


def test_malformed_executed_at_fails() -> None:
    packet = packet_with_checks()
    packet["check_results"][0]["executed_at"] = "not-a-timestamp"
    with pytest.raises(validator.ValidationError):
        validator.validate_check_results(packet, declared_paths={"tracked.txt"})


def test_invalid_output_sha_fails() -> None:
    packet = packet_with_checks()
    packet["check_results"][0]["execution_evidence"]["output_sha256"] = "abc"
    with pytest.raises(validator.ValidationError):
        validator.validate_check_results(packet, declared_paths={"tracked.txt"})
