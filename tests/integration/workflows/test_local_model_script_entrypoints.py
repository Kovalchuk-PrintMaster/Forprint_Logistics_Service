from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def run_module(module_name: str) -> subprocess.CompletedProcess[str]:
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


def test_local_model_validator_module_entrypoint() -> None:
    completed = run_module("scripts.validation.check_local_model_examples")

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "Local model example validation passed." in completed.stdout


def test_local_model_preview_module_entrypoint() -> None:
    completed = run_module("scripts.previews.preview_local_logistics_model")

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "Live provider write" in completed.stdout
    assert "DISABLED" in completed.stdout
    assert "No external provider call was performed." in completed.stdout
