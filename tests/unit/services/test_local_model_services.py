from datetime import UTC, datetime

from app.domain import (
    AddressSnapshot,
    LogisticsNotificationType,
    LogisticsProvider,
    ProviderCapability,
    RecipientRef,
    ShipmentStatus,
)
from app.services import (
    NotificationEventService,
    ShipmentDraftService,
    TrackingEventService,
)
from app.storage import InMemoryLogisticsRepository


def build_repository() -> InMemoryLogisticsRepository:
    return InMemoryLogisticsRepository()


def test_shipment_service_creates_preview_only_draft() -> None:
    repository = build_repository()
    service = ShipmentDraftService(repository)

    provider = LogisticsProvider(
        provider_id="preview_provider",
        display_name="Preview Provider",
        capabilities=frozenset(
            {
                ProviderCapability.SHIPMENT_PAYLOAD_PREVIEW,
            }
        ),
    )
    recipient = RecipientRef(
        recipient_ref="recipient_preview_001",
        display_name="Synthetic Recipient",
    )
    destination = AddressSnapshot(
        country_code="UA",
        city="Test City",
        address_line_1="Test Street 1",
    )

    draft = service.create_preview(
        shipment_id="shipment_preview_001",
        external_order_ref="order_ref_001",
        provider=provider,
        recipient=recipient,
        destination=destination,
        package_description="Synthetic package",
        weight_kg=1.5,
    )

    assert draft.preview_only is True
    assert draft.live_provider_write is False
    assert draft.status is ShipmentStatus.PREVIEW_READY
    assert repository.get_shipment_draft(draft.shipment_id) is draft


def test_tracking_request_remains_local() -> None:
    repository = build_repository()
    service = TrackingEventService(repository)
    requested_at = datetime.now(UTC)

    request = service.create_local_request(
        provider_id="preview_provider",
        tracking_number="LOCAL-TRACK-001",
        requested_at=requested_at,
    )

    assert request.local_only is True
    assert request.provider_call_performed is False
    assert (
        repository.get_tracking_request(
            "preview_provider",
            "LOCAL-TRACK-001",
        )
        is request
    )


def test_tracking_service_records_local_event() -> None:
    repository = build_repository()
    service = TrackingEventService(repository)
    occurred_at = datetime.now(UTC)

    event = service.record_local_event(
        event_id="tracking_event_001",
        provider_id="preview_provider",
        tracking_number="LOCAL-TRACK-001",
        occurred_at=occurred_at,
        normalized_status=(ShipmentStatus.TRACKING_UPDATED),
        provider_status="local_status_update",
    )

    assert event.local_record is True
    assert repository.get_tracking_event(event.event_id) is event


def test_notification_service_creates_local_payload() -> None:
    repository = build_repository()
    service = NotificationEventService(repository)

    event = service.create_local_payload(
        event_id="notification_001",
        shipment_id="shipment_preview_001",
        event_type=(LogisticsNotificationType.TRACKING_STATUS_CHANGED),
        occurred_at=datetime.now(UTC),
        message="Local tracking update.",
    )

    assert event.local_payload is True
    assert event.delivery_performed is False
    assert repository.get_notification_event(event.event_id) is event
