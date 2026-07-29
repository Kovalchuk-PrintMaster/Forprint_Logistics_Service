from pathlib import Path

import yaml

from scripts.previews.preview_tracking_events_contract import (
    REQUIRED_SAFETY_FLAGS,
    build_tracking_events_preview,
)

FIXTURE_PATH = Path("examples/fixtures/tracking_events/synthetic_tracking_events.yaml")


def load_fixture() -> dict:
    data = yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_tracking_events_fixture_is_synthetic_and_safe() -> None:
    data = load_fixture()

    assert data["synthetic_data"] is True
    assert data["real_customer_data"] is False

    for field_name, expected in REQUIRED_SAFETY_FLAGS.items():
        assert data[field_name] is expected

    text = FIXTURE_PATH.read_text(encoding="utf-8").casefold()

    for forbidden in (
        "api_key",
        "api_token",
        "access_token",
        "authorization",
        "password",
        "secret",
        "raw_response",
        "+380",
    ):
        assert forbidden not in text


def test_fixture_covers_required_event_and_replay_cases() -> None:
    data = load_fixture()
    serialized = str(data)

    for required in (
        "shipment_created",
        "tracking_updated",
        "arrived",
        "delivered",
        "failed",
        "needs_attention",
        "duplicate",
        "out_of_order",
    ):
        assert required in serialized


def test_fixture_builds_deterministic_preview() -> None:
    first = build_tracking_events_preview(FIXTURE_PATH)
    second = build_tracking_events_preview(FIXTURE_PATH)

    assert first.to_mapping() == second.to_mapping()
    assert first.notification_replay_stable is True
