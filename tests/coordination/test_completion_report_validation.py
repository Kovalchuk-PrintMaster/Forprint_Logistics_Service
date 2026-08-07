from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

from scripts.coordination.apply_completion_packet import apply_completion_packet
from scripts.coordination.validate_completion_report import validate_report
from tests.coordination.test_completion_packet_automation import build_packet, prepare_project_root


def test_generated_report_matches_packet(tmp_path: Path) -> None:
    prepare_project_root(tmp_path)
    packet = build_packet()
    packet_path = tmp_path / "packet.yaml"
    packet_path.write_text(yaml.safe_dump(packet, sort_keys=False), encoding="utf-8")
    apply_completion_packet(packet_path, tmp_path)
    report = tmp_path / packet["report_path"]
    assert validate_report(packet, report) == []


def test_report_mismatch_is_detected(tmp_path: Path) -> None:
    prepare_project_root(tmp_path)
    packet = build_packet()
    packet_path = tmp_path / "packet.yaml"
    packet_path.write_text(yaml.safe_dump(packet, sort_keys=False), encoding="utf-8")
    apply_completion_packet(packet_path, tmp_path)
    report = tmp_path / packet["report_path"]
    report.write_text(
        report.read_text(encoding="utf-8").replace("a" * 40, "b" * 40), encoding="utf-8"
    )
    assert any("implementation_commit" in error for error in validate_report(packet, report))


def test_report_validator_cli_entrypoint(tmp_path: Path) -> None:
    prepare_project_root(tmp_path)
    packet = build_packet()
    packet_path = tmp_path / "packet.yaml"
    packet_path.write_text(
        yaml.safe_dump(packet, sort_keys=False),
        encoding="utf-8",
    )
    apply_completion_packet(packet_path, tmp_path)
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts/coordination/validate_completion_report.py"
    result = subprocess.run(
        [sys.executable, str(script_path), str(packet_path)],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Completion report is consistent with packet" in result.stdout
