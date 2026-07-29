import json
from pathlib import Path

from scripts.previews.preview_tracking_events_contract import (
    DEFAULT_FIXTURE_PATH,
    build_tracking_events_preview,
    write_preview,
)


def test_tracking_events_preview_contains_all_safety_flags() -> None:
    preview = build_tracking_events_preview(DEFAULT_FIXTURE_PATH)
    data = preview.to_mapping()

    assert data["safety"] == {
        "preview_only": True,
        "live_write": False,
        "provider_call_performed": False,
        "telegram_api_call_performed": False,
        "cross_repository_write": False,
    }
    assert data["notification_replay_stable"] is True
    assert set(data["event_types_seen"]) == {
        "shipment_created",
        "tracking_updated",
        "arrived",
        "delivered",
        "failed",
        "needs_attention",
    }


def test_preview_writes_deterministic_json(tmp_path: Path) -> None:
    preview = build_tracking_events_preview(DEFAULT_FIXTURE_PATH)
    output_path = tmp_path / "tracking_events_preview.json"

    write_preview(preview, output_path)

    loaded = json.loads(output_path.read_text(encoding="utf-8"))

    assert loaded == preview.to_mapping()
    assert "telegram_message" not in output_path.read_text(encoding="utf-8")
    assert "telegram_buttons" not in output_path.read_text(encoding="utf-8")
