from datetime import UTC, datetime

import pytest

from app.domain import (
    AddressSnapshot,
    AddressValidationResult,
    DryRunExecutionMetadata,
    DryRunPayloadEnvelope,
    LogisticsProvider,
    ProviderCapability,
    ProviderCapabilityDescription,
    ProviderError,
    ProviderErrorCode,
    ProviderOperation,
    RecipientRef,
    RecipientValidationResult,
    ShipmentDraft,
    ShipmentPayloadPreviewResult,
    TrackingEvent,
    TrackingLookupRequest,
    TrackingLookupResult,
)


def build_provider() -> LogisticsProvider:
    return LogisticsProvider(
        provider_id="synthetic_parcel",
        display_name="Synthetic Parcel Provider",
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


def build_draft() -> ShipmentDraft:
    return ShipmentDraft(
        shipment_id="shipment_contract_001",
        external_order_ref="order_ref_001",
        provider_id="synthetic_parcel",
        recipient=RecipientRef(
            recipient_ref="test_recipient_001",
            display_name="Test Recipient",
        ),
        destination=AddressSnapshot(
            country_code="UA",
            city="Test City",
            address_line_1="Test Street 1",
        ),
        package_description="Synthetic package",
        weight_kg=1.0,
    )


def test_capability_discovery_is_deterministic() -> None:
    description = ProviderCapabilityDescription.from_provider(build_provider())

    values = [item.capability.value for item in description.capabilities]

    assert values == sorted(values)
    assert description.support_for(ProviderCapability.TRACKING).supported is True


def test_unsupported_capability_is_explicit() -> None:
    provider = build_provider()

    support = provider.capability_support(ProviderCapability.DELIVERY_QUOTE_LOOKUP)

    assert support.supported is False
    assert support.reason_code == "unsupported_capability"


def test_live_write_capability_is_always_disabled() -> None:
    support = build_provider().operation_support(ProviderOperation.LIVE_SHIPMENT_CREATION)

    assert support.supported is False
    assert support.reason_code == "live_write_disabled"


def test_dry_run_metadata_rejects_live_execution() -> None:
    with pytest.raises(
        ValueError,
        match="Live provider writes",
    ):
        DryRunExecutionMetadata(
            operation=(ProviderOperation.SHIPMENT_PAYLOAD_PREVIEW),
            correlation_ref="request_001",
            live_write=True,
        )

    with pytest.raises(
        ValueError,
        match="Real provider calls",
    ):
        DryRunExecutionMetadata(
            operation=(ProviderOperation.TRACKING_LOOKUP),
            correlation_ref="request_002",
            provider_call_performed=True,
        )


def test_preview_envelope_is_unmistakably_non_live() -> None:
    execution = DryRunExecutionMetadata(
        operation=(ProviderOperation.SHIPMENT_PAYLOAD_PREVIEW),
        correlation_ref="request_003",
    )

    envelope = DryRunPayloadEnvelope(
        provider_id="synthetic_parcel",
        schema_version=("provider_payload_preview_v0_1"),
        execution=execution,
        normalized_input_summary=(
            ("shipment_id", "shipment_contract_001"),
            ("weight_kg", "1.0"),
        ),
        provider_payload_preview=(
            ("service_type", "parcel"),
            ("shipment_id", "shipment_contract_001"),
        ),
        warnings=("Synthetic preview only.",),
    )

    result = ShipmentPayloadPreviewResult(envelope=envelope)

    assert result.successful is True
    assert envelope.preview_only is True
    assert envelope.live_write is False
    assert envelope.payload_mapping()["service_type"] == "parcel"


def test_preview_payload_rejects_sensitive_keys() -> None:
    with pytest.raises(
        ValueError,
        match="sensitive provider values",
    ):
        DryRunPayloadEnvelope(
            provider_id="synthetic_parcel",
            schema_version="preview_v0_1",
            execution=DryRunExecutionMetadata(
                operation=(ProviderOperation.SHIPMENT_PAYLOAD_PREVIEW),
                correlation_ref="request_004",
            ),
            normalized_input_summary=(),
            provider_payload_preview=(("api_token", "unsafe"),),
        )


def test_validation_result_operation_is_typed() -> None:
    recipient_result = RecipientValidationResult(
        provider_id="synthetic_parcel",
        execution=DryRunExecutionMetadata(
            operation=(ProviderOperation.RECIPIENT_VALIDATION),
            correlation_ref="request_005",
        ),
        valid=True,
    )

    assert recipient_result.valid is True

    with pytest.raises(
        ValueError,
        match="wrong operation",
    ):
        AddressValidationResult(
            provider_id="synthetic_parcel",
            execution=DryRunExecutionMetadata(
                operation=(ProviderOperation.RECIPIENT_VALIDATION),
                correlation_ref="request_006",
            ),
            valid=True,
        )


def test_invalid_result_may_contain_typed_error() -> None:
    error = ProviderError.from_code(
        ProviderErrorCode.RECIPIENT_VALIDATION_FAILED,
        provider_id="synthetic_parcel",
        operation=(ProviderOperation.RECIPIENT_VALIDATION),
    )

    result = RecipientValidationResult(
        provider_id="synthetic_parcel",
        execution=DryRunExecutionMetadata(
            operation=(ProviderOperation.RECIPIENT_VALIDATION),
            correlation_ref="request_007",
        ),
        valid=False,
        errors=(error,),
    )

    assert result.errors == (error,)


def test_tracking_contract_remains_local_and_typed() -> None:
    request = TrackingLookupRequest(
        provider_id="synthetic_parcel",
        tracking_number="TRACK-001",
        correlation_ref="request_008",
    )
    event = TrackingEvent(
        event_id="event_001",
        provider_id=request.provider_id,
        tracking_number=request.tracking_number,
        occurred_at=datetime.now(UTC),
        normalized_status="tracking",
        provider_status="synthetic_tracking",
    )

    result = TrackingLookupResult(
        provider_id=request.provider_id,
        tracking_number=request.tracking_number,
        correlation_ref=request.correlation_ref,
        events=(event,),
    )

    assert result.read_only is True
    assert result.provider_call_performed is False
    assert result.events == (event,)
