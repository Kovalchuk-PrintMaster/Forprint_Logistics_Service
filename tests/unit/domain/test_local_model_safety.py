from datetime import UTC, datetime

import pytest

from app.domain import (
    AddressSnapshot,
    LogisticsNotificationEvent,
    LogisticsNotificationType,
    RecipientRef,
    ShipmentDraft,
    TrackingEvent,
    TrackingRequest,
)
from app.domain.shipments import ShipmentStatus


def build_recipient() -> RecipientRef:
    return RecipientRef(
        recipient_ref="recipient_001",
        display_name="Synthetic Recipient",
    )


def build_address() -> AddressSnapshot:
    return AddressSnapshot(
        country_code="UA",
        city="Test City",
        address_line_1="Test Street 1",
    )


def test_recipient_cannot_claim_canonical_ownership() -> None:
    with pytest.raises(
        ValueError,
        match="non-canonical",
    ):
        RecipientRef(
            recipient_ref="recipient_001",
            display_name="Unsafe Recipient",
            non_canonical=False,
        )


def test_address_must_be_shipment_time_snapshot() -> None:
    with pytest.raises(
        ValueError,
        match="shipment-time snapshots",
    ):
        AddressSnapshot(
            country_code="UA",
            city="Test City",
            address_line_1="Test Street 1",
            shipment_time_snapshot=False,
        )


def test_shipment_draft_must_be_preview_only() -> None:
    with pytest.raises(
        ValueError,
        match="preview-only",
    ):
        ShipmentDraft(
            shipment_id="shipment_001",
            external_order_ref="order_ref_001",
            provider_id="provider_001",
            recipient=build_recipient(),
            destination=build_address(),
            package_description="Test package",
            weight_kg=1.0,
            preview_only=False,
        )


def test_shipment_draft_rejects_live_write() -> None:
    with pytest.raises(
        ValueError,
        match="Live provider writes",
    ):
        ShipmentDraft(
            shipment_id="shipment_001",
            external_order_ref="order_ref_001",
            provider_id="provider_001",
            recipient=build_recipient(),
            destination=build_address(),
            package_description="Test package",
            weight_kg=1.0,
            live_provider_write=True,
        )


def test_tracking_request_must_remain_local() -> None:
    with pytest.raises(
        ValueError,
        match="local-only",
    ):
        TrackingRequest(
            provider_id="provider_001",
            tracking_number="TRACK-001",
            requested_at=datetime.now(UTC),
            local_only=False,
        )


def test_tracking_request_rejects_provider_call() -> None:
    with pytest.raises(
        ValueError,
        match="Provider tracking calls",
    ):
        TrackingRequest(
            provider_id="provider_001",
            tracking_number="TRACK-001",
            requested_at=datetime.now(UTC),
            provider_call_performed=True,
        )


def test_tracking_event_must_be_local_record() -> None:
    with pytest.raises(
        ValueError,
        match="local records",
    ):
        TrackingEvent(
            event_id="event_001",
            provider_id="provider_001",
            tracking_number="TRACK-001",
            occurred_at=datetime.now(UTC),
            normalized_status=ShipmentStatus.TRACKING,
            provider_status="local_status",
            local_record=False,
        )


def test_notification_rejects_real_delivery() -> None:
    with pytest.raises(
        ValueError,
        match="delivery is disabled",
    ):
        LogisticsNotificationEvent(
            event_id="notification_001",
            shipment_id="shipment_001",
            event_type=(LogisticsNotificationType.TRACKING_STATUS_CHANGED),
            occurred_at=datetime.now(UTC),
            message="Local message",
            delivery_performed=True,
        )
