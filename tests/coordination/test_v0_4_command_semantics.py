from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _block(text: str, start: str, end: str) -> str:
    return text.split(start, 1)[1].split(end, 1)[0]


def test_completion_packet_check_is_read_only() -> None:
    text = (ROOT / "Makefile").read_text(encoding="utf-8")
    block = _block(
        text,
        ".PHONY: completion-packet-check",
        ".PHONY: report-clean",
    )
    assert "completion-packet-apply" not in block
    assert "completion-packet-validate" in block
    assert "completion-report-validate" in block


def test_module_validate_has_no_cleanup_or_status_mutation() -> None:
    text = (ROOT / "Makefile").read_text(encoding="utf-8")
    block = _block(
        text,
        ".PHONY: module-validate",
        "# =============================================================================",
    )
    assert "report-clean" not in block
    assert "status-report" not in block
    assert "check-report-full" in block
    assert "governance-check" in block
    assert "coordination-check" in block


def test_check_report_targets_are_read_only_and_generation_is_explicit() -> None:
    text = (ROOT / "Makefile").read_text(encoding="utf-8")
    block = _block(
        text,
        ".PHONY: check-report",
        "# =============================================================================",
    )
    assert "run_logistics_checks_read_only.py" in block
    assert "check-report-generate:" in block
    assert "check-report-full-generate:" in block


def test_v04_validator_targets_are_exposed() -> None:
    text = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "completion-packet-v0-4-validate:" in text
    assert "completion-outbox-v0-4-validate:" in text


def test_module_owned_v04_validators_exist() -> None:
    assert (ROOT / "scripts/coordination/validate_completion_packet_v0_4.py").is_file()
    assert (ROOT / "scripts/coordination/validate_completion_outbox_v0_4.py").is_file()
