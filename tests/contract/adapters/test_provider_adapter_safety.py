from __future__ import annotations

from typing import get_type_hints

import pytest

from app.adapters.providers import (
    LiveProviderWriteDisabledError,
    ProviderAdapter,
)
from app.domain import (
    AddressSnapshot,
    AddressValidationRequest,
    AddressValidationResult,
    DeliveryQuoteLookupRequest,
    DeliveryQuoteLookupResult,
    DryRunExecutionMetadata,
    DryRunPayloadEnvelope,
    LogisticsProvider,
    ProviderCapability,
    ProviderCapabilityDescription,
    ProviderErrorCode,
    ProviderOperation,
    RecipientRef,
    RecipientValidationRequest,
    RecipientValidationResult,
    ShipmentDraft,
    ShipmentPayloadPreviewRequest,
    ShipmentPayloadPreviewResult,
    TrackingLookupRequest,
    TrackingLookupResult,
)


class FakeTypedAdapter(ProviderAdapter):
    def __init__(self) -> None:
        self._provider = LogisticsProvider(
            provider_id="fake_preview_provider",
            display_name="Fake Preview Provider",
            capabilities=frozenset(
                {
                    ProviderCapability.CAPABILITY_DESCRIPTION,
                    ProviderCapability.RECIPIENT_VALIDATION,
                    ProviderCapability.ADDRESS_VALIDATION,
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
        request: RecipientValidationRequest,
    ) -> RecipientValidationResult:
        return RecipientValidationResult(
            provider_id=self.provider.provider_id,
            execution=DryRunExecutionMetadata(
                operation=(ProviderOperation.RECIPIENT_VALIDATION),
                correlation_ref=request.correlation_ref,
            ),
            valid=True,
        )

    def validate_address(
        self,
        request: AddressValidationRequest,
    ) -> AddressValidationResult:
        return AddressValidationResult(
            provider_id=self.provider.provider_id,
            execution=DryRunExecutionMetadata(
                operation=(ProviderOperation.ADDRESS_VALIDATION),
                correlation_ref=request.correlation_ref,
            ),
            valid=True,
        )

    def build_shipment_payload_preview(
        self,
        request: ShipmentPayloadPreviewRequest,
    ) -> ShipmentPayloadPreviewResult:
        envelope = DryRunPayloadEnvelope(
            provider_id=self.provider.provider_id,
            schema_version=("fake_provider_payload_preview_v0_1"),
            execution=DryRunExecutionMetadata(
                operation=(ProviderOperation.SHIPMENT_PAYLOAD_PREVIEW),
                correlation_ref=request.correlation_ref,
            ),
            normalized_input_summary=(
                (
                    "shipment_id",
                    request.draft.shipment_id,
                ),
            ),
            provider_payload_preview=(
                ("preview", True),
                (
                    "shipment_id",
                    request.draft.shipment_id,
                ),
            ),
        )

        return ShipmentPayloadPreviewResult(envelope=envelope)

    def track(
        self,
        request: TrackingLookupRequest,
    ) -> TrackingLookupResult:
        return TrackingLookupResult(
            provider_id=self.provider.provider_id,
            tracking_number=request.tracking_number,
            correlation_ref=request.correlation_ref,
        )


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


def test_adapter_capability_description_is_typed() -> None:
    adapter = FakeTypedAdapter()
    description = adapter.describe_capabilities()

    assert isinstance(
        description,
        ProviderCapabilityDescription,
    )
    assert description.support_for(ProviderCapability.TRACKING).supported is True


def test_adapter_validations_return_typed_results() -> None:
    adapter = FakeTypedAdapter()
    draft = build_test_draft()

    recipient_result = adapter.validate_recipient(
        RecipientValidationRequest(
            correlation_ref="recipient_request_001",
            recipient=draft.recipient,
            address=draft.destination,
        )
    )
    address_result = adapter.validate_address(
        AddressValidationRequest(
            correlation_ref="address_request_001",
            address=draft.destination,
        )
    )

    assert isinstance(
        recipient_result,
        RecipientValidationResult,
    )
    assert isinstance(
        address_result,
        AddressValidationResult,
    )
    assert recipient_result.valid is True
    assert address_result.valid is True


def test_adapter_builds_typed_preview_envelope() -> None:
    adapter = FakeTypedAdapter()

    result = adapter.build_shipment_payload_preview(
        ShipmentPayloadPreviewRequest(
            correlation_ref="preview_request_001",
            draft=build_test_draft(),
        )
    )

    assert isinstance(
        result,
        ShipmentPayloadPreviewResult,
    )
    assert result.successful is True
    assert result.envelope.preview_only is True
    assert result.envelope.live_write is False
    assert result.envelope.execution.provider_call_performed is False


def test_tracking_boundary_is_typed_and_read_only() -> None:
    adapter = FakeTypedAdapter()
    result = adapter.track(
        TrackingLookupRequest(
            provider_id=adapter.provider.provider_id,
            tracking_number="TEST-TRACK-001",
            correlation_ref="tracking_request_001",
        )
    )

    assert isinstance(
        result,
        TrackingLookupResult,
    )
    assert result.read_only is True
    assert result.provider_call_performed is False
    assert result.events == ()


def test_quote_lookup_is_explicitly_unavailable() -> None:
    adapter = FakeTypedAdapter()

    result = adapter.lookup_delivery_quote(
        DeliveryQuoteLookupRequest(
            provider_id=adapter.provider.provider_id,
            execution=DryRunExecutionMetadata(
                operation=(ProviderOperation.DELIVERY_QUOTE_LOOKUP),
                correlation_ref="quote_request_001",
            ),
            normalized_input_summary=(("weight_kg", "1.0"),),
        )
    )

    assert isinstance(
        result,
        DeliveryQuoteLookupResult,
    )
    assert result.available is False
    assert result.service_options == ()
    assert result.errors[0].code is ProviderErrorCode.UNSUPPORTED_CAPABILITY
    assert result.execution.provider_call_performed is False


def test_live_create_shipment_is_typed_and_disabled() -> None:
    adapter = FakeTypedAdapter()

    with pytest.raises(
        LiveProviderWriteDisabledError,
        match=("Live provider shipment creation is disabled"),
    ) as error_info:
        adapter.create_shipment(build_test_draft())

    provider_error = error_info.value.provider_error

    assert provider_error.code is ProviderErrorCode.LIVE_WRITE_DISABLED
    assert provider_error.retryable is False
    assert provider_error.operation is ProviderOperation.LIVE_SHIPMENT_CREATION


def test_adapter_public_boundary_has_typed_results() -> None:
    assert get_type_hints(ProviderAdapter.validate_recipient)["return"] is RecipientValidationResult
    assert get_type_hints(ProviderAdapter.validate_address)["return"] is AddressValidationResult
    assert (
        get_type_hints(ProviderAdapter.build_shipment_payload_preview)["return"]
        is ShipmentPayloadPreviewResult
    )
    assert get_type_hints(ProviderAdapter.track)["return"] is TrackingLookupResult
    assert (
        get_type_hints(ProviderAdapter.lookup_delivery_quote)["return"] is DeliveryQuoteLookupResult
    )
