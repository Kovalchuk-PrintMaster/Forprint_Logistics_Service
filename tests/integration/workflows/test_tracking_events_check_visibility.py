from __future__ import annotations

import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_tracking_events_check_is_visible_and_safe() -> None:
    completed = subprocess.run(
        ["make", "tracking-events-check"],
        cwd=PROJECT_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "Six canonical provider-neutral event types" in (completed.stdout)
    assert "no external calls or writes" in completed.stdout


def test_tracking_events_preview_entrypoint_is_read_only() -> None:
    completed = subprocess.run(
        [
            ".venv_logistics_service/bin/python",
            "-m",
            "scripts.previews.preview_tracking_events_contract",
            "--no-write",
        ],
        cwd=PROJECT_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "preview_only" not in completed.stderr
    assert "No provider, Telegram or cross-repository call" in (completed.stdout)
