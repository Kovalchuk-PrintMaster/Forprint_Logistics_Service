from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

import pytest

from app.adapters.providers import (
    LiveProviderWriteDisabledError,
    ProviderAdapter,
)
from app.domain import (
    AddressSnapshot,
    LogisticsProvider,
    ProviderCapability,
    RecipientRef,
    ShipmentDraft,
    TrackingEvent,
    TrackingRequest,
)


class FakePreviewOnlyAdapter(ProviderAdapter):
    def __init__(self) -> None:
        self._provider = LogisticsProvider(
            provider_id="fake_preview_provider",
            display_name="Fake Preview Provider",
            capabilities=frozenset(
                {
                    ProviderCapability.RECIPIENT_VALIDATION,
                    ProviderCapability.SHIPMENT_PAYLOAD_PREVIEW,
                    ProviderCapability.TRACKING,
                }
            ),
        )

    @property
    def provider(self) -> LogisticsProvider:
        return self._provider

    def validate_recipient(
        self,
        recipient: RecipientRef,
        address: AddressSnapshot,
    ) -> tuple[str, ...]:
        del recipient, address
        return ()

    def build_shipment_payload_preview(
        self,
        draft: ShipmentDraft,
    ) -> Mapping[str, object]:
        return {
            "preview": True,
            "provider_id": self.provider.provider_id,
            "shipment_id": draft.shipment_id,
        }

    def track(self, request: TrackingRequest) -> Sequence[TrackingEvent]:
        del request
        return ()


def build_test_draft() -> ShipmentDraft:
    return ShipmentDraft(
        shipment_id="shipment_test_001",
        external_order_ref="order_ref_001",
        provider_id="fake_preview_provider",
        recipient=RecipientRef(
            recipient_ref="test_recipient_001",
            display_name="Test Recipient",
        ),
        destination=AddressSnapshot(
            country_code="UA",
            city="Test City",
            address_line_1="Test Street 1",
        ),
        package_description="Local test package",
        weight_kg=1.0,
    )


def test_adapter_can_build_preview_without_provider_write() -> None:
    adapter = FakePreviewOnlyAdapter()
    preview = adapter.build_shipment_payload_preview(build_test_draft())

    assert preview["preview"] is True
    assert preview["provider_id"] == "fake_preview_provider"


def test_adapter_live_create_shipment_is_disabled() -> None:
    adapter = FakePreviewOnlyAdapter()

    with pytest.raises(
        LiveProviderWriteDisabledError,
        match="Live provider shipment creation is disabled",
    ):
        adapter.create_shipment(build_test_draft())


def test_tracking_read_boundary_is_available() -> None:
    adapter = FakePreviewOnlyAdapter()

    request = TrackingRequest(
        provider_id=adapter.provider.provider_id,
        tracking_number="TEST-TRACK-001",
        requested_at=datetime.now(UTC),
    )

    assert adapter.track(request) == ()
