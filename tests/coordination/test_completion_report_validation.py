from __future__ import annotations

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
