from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "coordination/evidence/tracking_events_v0_4/source_obligation_audit.yaml"
TELEGRAM = ROOT / "coordination/evidence/tracking_events_v0_4/telegram_handoff.yaml"


def test_v04_source_obligation_audit_is_complete() -> None:
    data = yaml.safe_load(AUDIT.read_text(encoding="utf-8"))
    rows = data["source_obligations"]
    assert len(rows) == 26
    assert len({row["source_obligation_id"] for row in rows}) == 26
    assert all(row["remaining_gap"] is False for row in rows)


def test_v04_telegram_handoff_has_all_six_examples() -> None:
    data = yaml.safe_load(TELEGRAM.read_text(encoding="utf-8"))
    assert set(data["examples_by_event_type"]) == {
        "shipment_created",
        "tracking_updated",
        "arrived",
        "delivered",
        "failed",
        "needs_attention",
    }
    assert data["event_type_coverage"] == "6/6"


def test_tracking_events_preview_make_target_is_read_only() -> None:
    text = (ROOT / "Makefile").read_text(encoding="utf-8")
    preview = text.split("tracking-events-preview:", 1)[1].split(
        ".PHONY: tracking-events-preview-generate", 1
    )[0]
    assert "--no-write" in preview
    generate = text.split("tracking-events-preview-generate:", 1)[1].split(".PHONY:", 1)[0]
    assert "--no-write" not in generate
