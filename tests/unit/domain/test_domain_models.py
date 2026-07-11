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
    TrackingRequest,
)


def test_provider_neutral_domain_models_can_be_created() -> None:
    provider = LogisticsProvider(
        provider_id="test_provider",
        display_name="Test Provider",
        capabilities=frozenset(
            {
                ProviderCapability.RECIPIENT_VALIDATION,
                ProviderCapability.SHIPMENT_PAYLOAD_PREVIEW,
                ProviderCapability.TRACKING,
            }
        ),
    )

    recipient = RecipientRef(
        recipient_ref="test_recipient_001",
        display_name="Test Recipient",
        phone="+380000000001",
    )

    address = AddressSnapshot(
        country_code="UA",
        city="Test City",
        address_line_1="Test Street 1",
        postal_code="00001",
    )

    draft = ShipmentDraft(
        shipment_id="shipment_test_001",
        external_order_ref="order_ref_001",
        provider_id=provider.provider_id,
        recipient=recipient,
        destination=address,
        package_description="Safe test package",
        weight_kg=1.25,
    )

    requested_at = datetime.now(UTC)

    tracking_request = TrackingRequest(
        provider_id=provider.provider_id,
        tracking_number="TEST-TRACK-001",
        requested_at=requested_at,
    )

    tracking_event = TrackingEvent(
        event_id="tracking_event_001",
        provider_id=provider.provider_id,
        tracking_number=tracking_request.tracking_number,
        occurred_at=requested_at,
        normalized_status=ShipmentStatus.TRACKING,
        provider_status="test_in_transit",
    )

    notification = LogisticsNotificationEvent(
        event_id="notification_001",
        shipment_id=draft.shipment_id,
        event_type=LogisticsNotificationType.TRACKING_STATUS_CHANGED,
        occurred_at=requested_at,
        message="Tracking status changed in a local test.",
    )

    assert provider.supports(ProviderCapability.TRACKING)
    assert draft.status is ShipmentStatus.DRAFT
    assert tracking_event.normalized_status is ShipmentStatus.TRACKING
    assert notification.shipment_id == draft.shipment_id


def test_live_write_provider_configuration_is_rejected() -> None:
    with pytest.raises(ValueError, match="Live provider writes are disabled"):
        LogisticsProvider(
            provider_id="unsafe_provider",
            display_name="Unsafe Provider",
            live_write_enabled=True,
        )


def test_live_creation_capability_is_rejected() -> None:
    with pytest.raises(ValueError, match="LIVE_SHIPMENT_CREATION"):
        LogisticsProvider(
            provider_id="unsafe_provider",
            display_name="Unsafe Provider",
            capabilities=frozenset(
                {
                    ProviderCapability.LIVE_SHIPMENT_CREATION,
                }
            ),
        )
