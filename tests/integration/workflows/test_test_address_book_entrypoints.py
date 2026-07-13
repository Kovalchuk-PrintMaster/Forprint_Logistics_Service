from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def run_module(
    module_name: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            module_name,
        ],
        cwd=PROJECT_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )


def test_address_book_validator_entrypoint() -> None:
    completed = run_module("scripts.validation.check_test_address_book")

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "Test address book validation passed." in completed.stdout


def test_address_book_preview_entrypoint() -> None:
    completed = run_module("scripts.previews.preview_test_address_book")

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "Entry count: 3" in completed.stdout
    assert "Lookup by alias: OK" in completed.stdout
    assert "Live provider write: disabled" in completed.stdout
    assert "No external provider call was performed." in completed.stdout
