from datetime import UTC, datetime, timedelta

import pytest

from app.domain import (
    TRACKING_EVENT_SCHEMA_VERSION,
    LogisticsNotificationProjection,
    NotificationPriority,
    ProviderTrackingObservation,
    ShipmentEventEnvelope,
    ShipmentEventType,
    ShipmentStatus,
)

NOW = datetime(2026, 7, 29, 10, 0, tzinfo=UTC)


def build_event(
    **overrides: object,
) -> ShipmentEventEnvelope:
    values: dict[str, object] = {
        "event_id": "event_001",
        "event_type": ShipmentEventType.ARRIVED,
        "event_version": TRACKING_EVENT_SCHEMA_VERSION,
        "occurred_at": NOW,
        "recorded_at": NOW + timedelta(minutes=1),
        "shipment_reference": "shipment_001",
        "tracking_reference": "TRACK-001",
        "provider_id": "synthetic_parcel",
        "provider_event_code": "AT_DESTINATION",
        "previous_state": ShipmentStatus.TRACKING_UPDATED,
        "current_state": ShipmentStatus.ARRIVED,
        "correlation_id": "correlation_001",
        "causation_id": "event_000",
        "idempotency_key": "event_idem_001",
        "source": "logistics_service",
        "details": (
            ("provider_status", "at_destination"),
            ("terminal", "kyiv_001"),
        ),
        "safe_summary": "Shipment arrival was recorded.",
    }
    values.update(overrides)
    return ShipmentEventEnvelope(**values)


def test_canonical_event_taxonomy_is_exact() -> None:
    assert {item.value for item in ShipmentEventType} == {
        "shipment_created",
        "tracking_updated",
        "arrived",
        "delivered",
        "failed",
        "needs_attention",
    }


def test_event_envelope_is_typed_versioned_and_safe() -> None:
    event = build_event()

    assert event.event_version == TRACKING_EVENT_SCHEMA_VERSION
    assert event.current_state is ShipmentStatus.ARRIVED
    assert event.preview_only is True
    assert event.live_write is False
    assert event.provider_call_performed is False
    assert event.telegram_api_call_performed is False
    assert event.cross_repository_write is False


def test_event_envelope_rejects_naive_time_and_unknown_version() -> None:
    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        build_event(
            occurred_at=datetime(2026, 7, 29, 10, 0),
            recorded_at=None,
        )

    with pytest.raises(
        ValueError,
        match="Unsupported tracking event version",
    ):
        build_event(event_version="tracking_event_v9")


def test_event_envelope_rejects_state_mismatch() -> None:
    with pytest.raises(
        ValueError,
        match="do not match",
    ):
        build_event(
            current_state=ShipmentStatus.DELIVERED,
        )


def test_event_serialization_is_deterministic() -> None:
    first = build_event()
    second = build_event(
        details=(
            ("terminal", "kyiv_001"),
            ("provider_status", "at_destination"),
        )
    )

    assert first.to_json() == second.to_json()
    assert first.to_mapping()["details"] == {
        "provider_status": "at_destination",
        "terminal": "kyiv_001",
    }


def test_event_rejects_sensitive_details() -> None:
    with pytest.raises(
        ValueError,
        match="sensitive values",
    ):
        build_event(
            details=(("api_token", "unsafe"),),
        )


@pytest.mark.parametrize(
    "field_name",
    (
        "live_write",
        "provider_call_performed",
        "telegram_api_call_performed",
        "cross_repository_write",
    ),
)
def test_event_rejects_unsafe_execution_flags(
    field_name: str,
) -> None:
    with pytest.raises(ValueError):
        build_event(**{field_name: True})


def test_provider_observation_has_deterministic_identity() -> None:
    first = ProviderTrackingObservation(
        shipment_reference="shipment_001",
        provider_id="synthetic_parcel",
        provider_status="in_transit",
        provider_event_code="MOVING",
        tracking_reference="TRACK-001",
        occurred_at=NOW,
        safe_metadata=(
            ("terminal", "kyiv_001"),
            ("route", "north"),
        ),
    )
    second = ProviderTrackingObservation(
        shipment_reference="shipment_001",
        provider_id="synthetic_parcel",
        provider_status="in_transit",
        provider_event_code="MOVING",
        tracking_reference="TRACK-001",
        occurred_at=NOW,
        safe_metadata=(
            ("route", "north"),
            ("terminal", "kyiv_001"),
        ),
    )

    assert first.logical_fingerprint == second.logical_fingerprint


def test_notification_projection_is_channel_neutral() -> None:
    projection = LogisticsNotificationProjection.from_event(
        build_event(),
        recipient_reference="recipient_hint_001",
    )
    data = projection.to_mapping()

    assert projection.priority is NotificationPriority.NORMAL
    assert projection.preview_only is True
    assert projection.telegram_api_call_performed is False
    assert projection.cross_repository_write is False
    assert "message" not in data
    assert "buttons" not in data
    assert "chat_state" not in data
    assert data["facts"]["current_state"] == "arrived"


def test_notification_projection_serialization_is_deterministic() -> None:
    event = build_event()

    first = LogisticsNotificationProjection.from_event(event)
    second = LogisticsNotificationProjection.from_event(event)

    assert first.notification_key == second.notification_key
    assert first.idempotency_key == second.idempotency_key
    assert first.to_json() == second.to_json()
