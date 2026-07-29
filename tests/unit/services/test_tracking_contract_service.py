from datetime import UTC, datetime, timedelta

from app.domain import (
    ProviderTrackingObservation,
    ShipmentEventType,
    ShipmentStatus,
    TrackingProcessingDecision,
)
from app.services import TrackingContractService

BASE_TIME = datetime(2026, 7, 29, 10, 0, tzinfo=UTC)


def observation(
    provider_status: str,
    *,
    minutes: int,
    provider_event_code: str | None = None,
) -> ProviderTrackingObservation:
    return ProviderTrackingObservation(
        shipment_reference="shipment_001",
        provider_id="synthetic_parcel",
        provider_status=provider_status,
        provider_event_code=provider_event_code,
        tracking_reference="TRACK-001",
        occurred_at=BASE_TIME + timedelta(minutes=minutes),
        safe_metadata=(("fixture", "tracking_events_v0_1"),),
    )


def accept(
    service: TrackingContractService,
    item: ProviderTrackingObservation,
    history: tuple = (),
):
    result = service.process_observation(
        item,
        correlation_id="correlation_001",
        history=history,
        recipient_reference="recipient_hint_001",
    )
    assert result.decision is TrackingProcessingDecision.ACCEPTED
    assert result.event is not None
    assert result.notification is not None
    return result


def test_full_shipment_lifecycle_is_deterministic() -> None:
    service = TrackingContractService()

    created = accept(
        service,
        observation(
            "shipment_created",
            minutes=0,
            provider_event_code="CREATED",
        ),
    )
    tracking = accept(
        service,
        observation(
            "in_transit",
            minutes=10,
            provider_event_code="MOVING",
        ),
        (created.event,),
    )
    arrived = accept(
        service,
        observation(
            "arrived",
            minutes=20,
            provider_event_code="ARRIVED",
        ),
        (
            created.event,
            tracking.event,
        ),
    )
    delivered = accept(
        service,
        observation(
            "delivered",
            minutes=30,
            provider_event_code="DELIVERED",
        ),
        (
            created.event,
            tracking.event,
            arrived.event,
        ),
    )

    assert created.event.event_type is (ShipmentEventType.SHIPMENT_CREATED)
    assert tracking.event.current_state is (ShipmentStatus.TRACKING_UPDATED)
    assert arrived.event.current_state is ShipmentStatus.ARRIVED
    assert delivered.event.current_state is (ShipmentStatus.DELIVERED)
    assert tracking.event.causation_id == created.event.event_id
    assert arrived.event.causation_id == tracking.event.event_id
    assert delivered.event.causation_id == arrived.event.event_id


def test_reprocessing_same_input_is_duplicate_safe() -> None:
    service = TrackingContractService()
    source = observation(
        "shipment_created",
        minutes=0,
        provider_event_code="CREATED",
    )
    first = accept(service, source)

    replay = service.process_observation(
        source,
        correlation_id="correlation_001",
        history=(first.event,),
        recipient_reference="recipient_hint_001",
    )

    assert replay.decision is (TrackingProcessingDecision.DUPLICATE)
    assert replay.event is first.event
    assert replay.notification is None


def test_repeated_newer_tracking_status_is_accepted() -> None:
    service = TrackingContractService()
    created = accept(
        service,
        observation("shipment_created", minutes=0),
    )
    first_update = accept(
        service,
        observation("tracking_updated", minutes=10),
        (created.event,),
    )
    second_update = accept(
        service,
        observation("tracking_updated", minutes=20),
        (
            created.event,
            first_update.event,
        ),
    )

    assert first_update.event.event_id != second_update.event.event_id
    assert second_update.event.previous_state is (ShipmentStatus.TRACKING_UPDATED)


def test_out_of_order_observation_does_not_emit_event() -> None:
    service = TrackingContractService()
    created = accept(
        service,
        observation("shipment_created", minutes=10),
    )

    result = service.process_observation(
        observation("tracking_updated", minutes=5),
        correlation_id="correlation_001",
        history=(created.event,),
    )

    assert result.decision is (TrackingProcessingDecision.OUT_OF_ORDER)
    assert result.event is None
    assert result.notification is None


def test_invalid_transition_is_rejected() -> None:
    service = TrackingContractService()
    created = accept(
        service,
        observation("shipment_created", minutes=0),
    )

    result = service.process_observation(
        observation("delivered", minutes=10),
        correlation_id="correlation_001",
        history=(created.event,),
    )

    assert result.decision is (TrackingProcessingDecision.INVALID_TRANSITION)
    assert result.event is None


def test_terminal_state_rejects_new_event() -> None:
    service = TrackingContractService()
    created = accept(
        service,
        observation("shipment_created", minutes=0),
    )
    updated = accept(
        service,
        observation("tracking_updated", minutes=10),
        (created.event,),
    )
    arrived = accept(
        service,
        observation("arrived", minutes=20),
        (
            created.event,
            updated.event,
        ),
    )
    delivered = accept(
        service,
        observation("delivered", minutes=30),
        (
            created.event,
            updated.event,
            arrived.event,
        ),
    )

    result = service.process_observation(
        observation("failed", minutes=40),
        correlation_id="correlation_001",
        history=(
            created.event,
            updated.event,
            arrived.event,
            delivered.event,
        ),
    )

    assert result.decision is (TrackingProcessingDecision.TERMINAL_STATE)
    assert result.event is None


def test_failure_and_needs_attention_paths_are_supported() -> None:
    service = TrackingContractService()
    created = accept(
        service,
        observation("shipment_created", minutes=0),
    )
    attention = accept(
        service,
        observation("needs_attention", minutes=10),
        (created.event,),
    )
    failed = accept(
        service,
        observation("failed", minutes=20),
        (
            created.event,
            attention.event,
        ),
    )

    assert attention.event.event_type is (ShipmentEventType.NEEDS_ATTENTION)
    assert failed.event.event_type is ShipmentEventType.FAILED


def test_unknown_provider_status_normalizes_to_attention() -> None:
    service = TrackingContractService()
    created = accept(
        service,
        observation("shipment_created", minutes=0),
    )

    result = accept(
        service,
        observation("provider_code_999", minutes=10),
        (created.event,),
    )

    assert result.event.event_type is (ShipmentEventType.NEEDS_ATTENTION)
    assert result.event.warnings


def test_notification_projection_replay_key_is_stable() -> None:
    service = TrackingContractService()
    first = accept(
        service,
        observation("shipment_created", minutes=0),
    )
    second = service.process_observation(
        observation("shipment_created", minutes=0),
        correlation_id="correlation_001",
        history=(),
        recipient_reference="recipient_hint_001",
    )

    assert second.notification is not None
    assert first.notification.notification_key == second.notification.notification_key
    assert first.notification.idempotency_key == second.notification.idempotency_key


def test_service_performs_no_external_actions() -> None:
    service = TrackingContractService()
    result = accept(
        service,
        observation("shipment_created", minutes=0),
    )

    assert result.event.preview_only is True
    assert result.event.live_write is False
    assert result.event.provider_call_performed is False
    assert result.event.telegram_api_call_performed is False
    assert result.event.cross_repository_write is False

    assert result.notification.preview_only is True
    assert result.notification.live_write is False
    assert result.notification.provider_call_performed is False
    assert result.notification.telegram_api_call_performed is False
    assert result.notification.cross_repository_write is False
