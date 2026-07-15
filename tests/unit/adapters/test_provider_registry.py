from __future__ import annotations

from dataclasses import fields

import pytest

from app.adapters.providers import (
    DuplicateProviderRegistrationError,
    ProviderAdapter,
    ProviderDisabledError,
    ProviderNotRegisteredError,
    ProviderRegistry,
    ProviderRegistryDescription,
)
from app.domain import (
    AddressValidationRequest,
    AddressValidationResult,
    DryRunExecutionMetadata,
    DryRunPayloadEnvelope,
    LogisticsProvider,
    ProviderCapability,
    ProviderOperation,
    RecipientValidationRequest,
    RecipientValidationResult,
    ShipmentPayloadPreviewRequest,
    ShipmentPayloadPreviewResult,
    TrackingLookupRequest,
    TrackingLookupResult,
)


class SyntheticRegistryAdapter(ProviderAdapter):
    def __init__(
        self,
        provider_id: str,
        capabilities: frozenset[ProviderCapability],
    ) -> None:
        self._provider = LogisticsProvider(
            provider_id=provider_id,
            display_name=(f"Synthetic {provider_id} Provider"),
            capabilities=capabilities,
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
        return ShipmentPayloadPreviewResult(
            envelope=DryRunPayloadEnvelope(
                provider_id=self.provider.provider_id,
                schema_version=("synthetic_registry_preview_v0_1"),
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
                provider_payload_preview=(("preview_only", True),),
            )
        )

    def track(
        self,
        request: TrackingLookupRequest,
    ) -> TrackingLookupResult:
        return TrackingLookupResult(
            provider_id=self.provider.provider_id,
            tracking_number=request.tracking_number,
            correlation_ref=request.correlation_ref,
        )


def build_adapter(
    provider_id: str = "synthetic_parcel",
    *,
    tracking: bool = True,
) -> SyntheticRegistryAdapter:
    capabilities = {
        ProviderCapability.CAPABILITY_DESCRIPTION,
        ProviderCapability.RECIPIENT_VALIDATION,
        ProviderCapability.ADDRESS_VALIDATION,
        ProviderCapability.SHIPMENT_PAYLOAD_PREVIEW,
    }

    if tracking:
        capabilities.add(ProviderCapability.TRACKING)

    return SyntheticRegistryAdapter(
        provider_id,
        frozenset(capabilities),
    )


def test_registration_is_disabled_by_default() -> None:
    registry = ProviderRegistry()

    entry = registry.register(build_adapter())

    assert entry.enabled is False
    assert len(registry) == 1
    assert registry.provider_ids() == ("synthetic_parcel",)
    assert registry.provider_ids(include_disabled=False) == ()


def test_disabled_provider_is_visible_but_not_resolved() -> None:
    adapter = build_adapter()
    registry = ProviderRegistry()
    registry.register(adapter)

    description = registry.describe(adapter.provider.provider_id)

    assert description.enabled is False
    assert description.live_write_enabled is False

    with pytest.raises(
        ProviderDisabledError,
        match="registered but disabled",
    ):
        registry.resolve(adapter.provider.provider_id)

    assert (
        registry.resolve(
            adapter.provider.provider_id,
            include_disabled=True,
        )
        is adapter
    )


def test_explicit_enabled_registration_can_resolve() -> None:
    adapter = build_adapter()
    registry = ProviderRegistry()

    registry.register(
        adapter,
        enabled=True,
        source="synthetic_test_fixture",
    )

    assert registry.resolve(adapter.provider.provider_id) is adapter
    assert registry.describe(adapter.provider.provider_id).source == "synthetic_test_fixture"


def test_duplicate_provider_id_is_rejected() -> None:
    registry = ProviderRegistry()
    registry.register(build_adapter("synthetic_parcel"))

    with pytest.raises(
        DuplicateProviderRegistrationError,
        match="already registered",
    ):
        registry.register(build_adapter("SYNTHETIC_PARCEL"))


def test_unknown_provider_lookup_is_explicit() -> None:
    registry = ProviderRegistry()

    with pytest.raises(
        ProviderNotRegisteredError,
        match="not registered",
    ):
        registry.resolve("missing_provider")


def test_capability_filter_is_deterministic() -> None:
    registry = ProviderRegistry()
    registry.register(
        build_adapter(
            "parcel_with_tracking",
            tracking=True,
        ),
        enabled=True,
    )
    registry.register(
        build_adapter(
            "courier_without_tracking",
            tracking=False,
        ),
        enabled=True,
    )
    registry.register(
        build_adapter(
            "disabled_tracking",
            tracking=True,
        ),
        enabled=False,
    )

    enabled = registry.filter_by_capability(ProviderCapability.TRACKING)
    all_matching = registry.filter_by_capability(
        ProviderCapability.TRACKING,
        include_disabled=True,
    )

    assert tuple(item.provider_id for item in enabled) == ("parcel_with_tracking",)

    assert tuple(item.provider_id for item in all_matching) == (
        "disabled_tracking",
        "parcel_with_tracking",
    )


def test_safe_description_exposes_no_adapter_or_secrets() -> None:
    registry = ProviderRegistry()
    registry.register(build_adapter())

    description = registry.describe("synthetic_parcel")
    field_names = {item.name for item in fields(ProviderRegistryDescription)}

    assert "adapter" not in field_names
    assert "credentials" not in field_names
    assert "token" not in field_names
    assert "secret" not in field_names
    assert description.live_write_enabled is False


def test_registry_performs_no_automatic_selection() -> None:
    registry = ProviderRegistry()
    registry.register(
        build_adapter("provider_a"),
        enabled=True,
    )
    registry.register(
        build_adapter("provider_b"),
        enabled=True,
    )

    assert registry.provider_ids(include_disabled=False) == (
        "provider_a",
        "provider_b",
    )
