from datetime import UTC, datetime

import pytest

from app.domain import (
    AddressSnapshot,
    LogisticsNotificationEvent,
    LogisticsNotificationType,
    LogisticsProvider,
    ProviderCapability,
    RecipientRef,
    ShipmentDraft,
    ShipmentStatus,
    TrackingEvent,
)
from app.storage import (
    InMemoryLogisticsRepository,
    LogisticsRepository,
    RepositoryReferenceError,
)


def build_provider(
    provider_id: str = "local_provider",
) -> LogisticsProvider:
    return LogisticsProvider(
        provider_id=provider_id,
        display_name="Local Preview Provider",
        capabilities=frozenset(
            {
                ProviderCapability.RECIPIENT_VALIDATION,
                ProviderCapability.SHIPMENT_PAYLOAD_PREVIEW,
                ProviderCapability.TRACKING,
            }
        ),
    )


def build_recipient(
    recipient_ref: str = "recipient_local_001",
) -> RecipientRef:
    return RecipientRef(
        recipient_ref=recipient_ref,
        display_name="Synthetic Recipient",
        phone="+380000000001",
        non_canonical=True,
    )


def build_draft(
    provider: LogisticsProvider,
    recipient: RecipientRef,
) -> ShipmentDraft:
    return ShipmentDraft(
        shipment_id="shipment_preview_001",
        external_order_ref="external_order_ref_001",
        provider_id=provider.provider_id,
        recipient=recipient,
        destination=AddressSnapshot(
            country_code="UA",
            city="Test City",
            address_line_1="Test Street 1",
            postal_code="00001",
        ),
        package_description="Synthetic test package",
        weight_kg=1.25,
        status=ShipmentStatus.DRAFT,
    )


def test_in_memory_repository_implements_protocol() -> None:
    repository = InMemoryLogisticsRepository()

    assert isinstance(
        repository,
        LogisticsRepository,
    )


def test_provider_and_recipient_save_get_list() -> None:
    repository = InMemoryLogisticsRepository()
    provider = build_provider()
    recipient = build_recipient()

    assert repository.save_provider(provider) is provider
    assert repository.save_recipient(recipient) is recipient

    assert repository.get_provider(provider.provider_id) is provider
    assert repository.get_recipient(recipient.recipient_ref) is recipient
    assert repository.list_providers() == (provider,)
    assert repository.list_recipients() == (recipient,)

    assert repository.get_provider("missing") is None
    assert repository.get_recipient("missing") is None


def test_shipment_draft_requires_known_local_refs() -> None:
    repository = InMemoryLogisticsRepository()
    provider = build_provider()
    recipient = build_recipient()
    draft = build_draft(provider, recipient)

    with pytest.raises(
        RepositoryReferenceError,
        match="unknown provider",
    ):
        repository.save_shipment_draft(draft)

    repository.save_provider(provider)

    with pytest.raises(
        RepositoryReferenceError,
        match="unknown recipient",
    ):
        repository.save_shipment_draft(draft)

    repository.save_recipient(recipient)

    assert repository.save_shipment_draft(draft) is draft
    assert repository.get_shipment_draft(draft.shipment_id) is draft
    assert repository.list_shipment_drafts() == (draft,)


def test_tracking_and_notification_events_are_local() -> None:
    repository = InMemoryLogisticsRepository()
    occurred_at = datetime.now(UTC)

    first_tracking_event = TrackingEvent(
        event_id="tracking_event_001",
        provider_id="local_provider",
        tracking_number="LOCAL-TRACK-001",
        occurred_at=occurred_at,
        normalized_status=ShipmentStatus.TRACKING,
        provider_status="local_in_transit",
    )
    second_tracking_event = TrackingEvent(
        event_id="tracking_event_002",
        provider_id="other_provider",
        tracking_number="LOCAL-TRACK-002",
        occurred_at=occurred_at,
        normalized_status=ShipmentStatus.DELIVERED,
        provider_status="local_delivered",
    )
    notification = LogisticsNotificationEvent(
        event_id="notification_001",
        shipment_id="shipment_preview_001",
        event_type=(LogisticsNotificationType.TRACKING_STATUS_CHANGED),
        occurred_at=occurred_at,
        message="Local tracking status changed.",
    )

    repository.save_tracking_event(first_tracking_event)
    repository.save_tracking_event(second_tracking_event)
    repository.save_notification_event(notification)

    assert repository.get_tracking_event(first_tracking_event.event_id) is first_tracking_event

    assert repository.list_tracking_events(provider_id="local_provider") == (first_tracking_event,)

    assert repository.list_tracking_events(tracking_number="LOCAL-TRACK-002") == (
        second_tracking_event,
    )

    assert repository.get_notification_event(notification.event_id) is notification

    assert repository.list_notification_events(shipment_id="shipment_preview_001") == (
        notification,
    )

    assert repository.list_notification_events(shipment_id="missing") == ()
