from __future__ import annotations

import pytest

from app.adapters.providers import (
    LiveProviderWriteDisabledError,
    SyntheticProviderClass,
    build_synthetic_provider_adapters,
    build_synthetic_provider_registry,
)
from app.domain import (
    AddressSnapshot,
    AddressValidationRequest,
    ProviderErrorCode,
    RecipientRef,
    ShipmentDraft,
    ShipmentPayloadPreviewRequest,
    TrackingLookupRequest,
)


def build_recipient() -> RecipientRef:
    return RecipientRef(
        recipient_ref="synthetic_recipient_001",
        display_name="Synthetic Recipient",
        phone="+380000000001",
        source_system="synthetic_contract_fixture",
    )


def build_address(
    *,
    postal_code: str | None = "00001",
) -> AddressSnapshot:
    return AddressSnapshot(
        country_code="UA",
        city="Synthetic City",
        address_line_1="Synthetic Street 1",
        postal_code=postal_code,
    )


def build_draft(provider_id: str) -> ShipmentDraft:
    return ShipmentDraft(
        shipment_id="synthetic_shipment_001",
        external_order_ref=("synthetic_order_ref_001"),
        provider_id=provider_id,
        recipient=build_recipient(),
        destination=build_address(),
        package_description="Synthetic package",
        weight_kg=1.25,
    )


def test_required_provider_classes_exist() -> None:
    adapters = build_synthetic_provider_adapters()

    assert tuple(adapter.profile.provider_class for adapter in adapters) == (
        SyntheticProviderClass.PARCEL,
        SyntheticProviderClass.POSTAL,
        SyntheticProviderClass.FREIGHT,
        SyntheticProviderClass.TAXI_COURIER,
    )


def test_synthetic_registry_contains_four_providers() -> None:
    registry = build_synthetic_provider_registry()

    assert registry.provider_ids() == (
        "synthetic_freight",
        "synthetic_parcel",
        "synthetic_postal",
        "synthetic_taxi_courier",
    )


def test_postal_provider_requires_postal_code() -> None:
    registry = build_synthetic_provider_registry()
    postal = registry.resolve("synthetic_postal")

    result = postal.validate_address(
        AddressValidationRequest(
            correlation_ref=("postal_validation_001"),
            address=build_address(postal_code=None),
        )
    )

    assert result.valid is False
    assert result.errors[0].code is ProviderErrorCode.ADDRESS_VALIDATION_FAILED


def test_parcel_preview_is_typed_and_non_live() -> None:
    registry = build_synthetic_provider_registry()
    parcel = registry.resolve("synthetic_parcel")
    draft = build_draft(parcel.provider.provider_id)

    result = parcel.build_shipment_payload_preview(
        ShipmentPayloadPreviewRequest(
            correlation_ref="preview_001",
            draft=draft,
        )
    )

    assert result.successful is True
    assert result.envelope.preview_only is True
    assert result.envelope.live_write is False
    assert result.envelope.execution.provider_call_performed is False
    assert result.envelope.payload_mapping()["provider_class"] == "parcel"


def test_taxi_courier_tracking_is_unsupported() -> None:
    registry = build_synthetic_provider_registry()
    courier = registry.resolve("synthetic_taxi_courier")

    result = courier.track(
        TrackingLookupRequest(
            provider_id=(courier.provider.provider_id),
            tracking_number=("SYNTHETIC-TRACK-001"),
            correlation_ref="tracking_001",
        )
    )

    assert result.read_only is True
    assert result.provider_call_performed is False
    assert result.events == ()
    assert result.errors[0].code is ProviderErrorCode.UNSUPPORTED_CAPABILITY


def test_every_synthetic_adapter_rejects_live_write() -> None:
    for adapter in build_synthetic_provider_adapters():
        with pytest.raises(
            LiveProviderWriteDisabledError,
            match="Live provider shipment creation",
        ):
            adapter.create_shipment(build_draft(adapter.provider.provider_id))
