from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.adapters.providers.base import ProviderAdapter
from app.adapters.providers.registry import ProviderRegistry
from app.domain.provider_contracts import (
    AddressValidationRequest,
    AddressValidationResult,
    DryRunExecutionMetadata,
    DryRunPayloadEnvelope,
    ProviderMessageLevel,
    ProviderValidationMessage,
    RecipientValidationRequest,
    RecipientValidationResult,
    ShipmentPayloadPreviewRequest,
    ShipmentPayloadPreviewResult,
    TrackingLookupRequest,
    TrackingLookupResult,
)
from app.domain.provider_errors import (
    ProviderError,
    ProviderErrorCode,
)
from app.domain.providers import (
    LogisticsProvider,
    ProviderCapability,
    ProviderOperation,
)


class SyntheticProviderClass(StrEnum):
    """Synthetic provider classes used for contract testing."""

    PARCEL = "parcel"
    POSTAL = "postal"
    FREIGHT = "freight"
    TAXI_COURIER = "taxi_courier"


@dataclass(frozen=True, slots=True)
class SyntheticProviderProfile:
    """Safe synthetic provider behavior definition."""

    provider_id: str
    display_name: str
    provider_class: SyntheticProviderClass
    service_type: str
    capabilities: frozenset[ProviderCapability]
    require_phone: bool = True
    require_postal_code: bool = False

    def __post_init__(self) -> None:
        provider_id = self.provider_id.strip()
        display_name = self.display_name.strip()
        service_type = self.service_type.strip()

        if not provider_id:
            raise ValueError("provider_id must not be empty")

        if not display_name:
            raise ValueError("display_name must not be empty")

        if not service_type:
            raise ValueError("service_type must not be empty")

        if ProviderCapability.LIVE_SHIPMENT_CREATION in self.capabilities:
            raise ValueError("Synthetic providers must not declare live shipment creation")

        if ProviderCapability.CAPABILITY_DESCRIPTION not in self.capabilities:
            raise ValueError("Synthetic providers must describe their capabilities")

        object.__setattr__(
            self,
            "provider_id",
            provider_id,
        )
        object.__setattr__(
            self,
            "display_name",
            display_name,
        )
        object.__setattr__(
            self,
            "service_type",
            service_type,
        )


class SyntheticProviderAdapter(ProviderAdapter):
    """Pure in-process adapter used for contract fixtures.

    It performs no HTTP, SDK, credential, database or provider-side
    operations.
    """

    def __init__(
        self,
        profile: SyntheticProviderProfile,
    ) -> None:
        self._profile = profile
        self._provider = LogisticsProvider(
            provider_id=profile.provider_id,
            display_name=profile.display_name,
            capabilities=profile.capabilities,
            live_write_enabled=False,
        )

    @property
    def profile(self) -> SyntheticProviderProfile:
        return self._profile

    @property
    def provider(self) -> LogisticsProvider:
        return self._provider

    def validate_recipient(
        self,
        request: RecipientValidationRequest,
    ) -> RecipientValidationResult:
        messages: list[ProviderValidationMessage] = []
        errors: list[ProviderError] = []

        if self.profile.require_phone and not (
            request.recipient.phone and request.recipient.phone.strip()
        ):
            messages.append(
                ProviderValidationMessage(
                    code="recipient_phone_required",
                    message=("Synthetic provider requires a recipient phone."),
                    level=ProviderMessageLevel.ERROR,
                    field_name="phone",
                )
            )
            errors.append(
                ProviderError.from_code(
                    ProviderErrorCode.RECIPIENT_VALIDATION_FAILED,
                    provider_id=(self.provider.provider_id),
                    operation=(ProviderOperation.RECIPIENT_VALIDATION),
                )
            )

        return RecipientValidationResult(
            provider_id=self.provider.provider_id,
            execution=DryRunExecutionMetadata(
                operation=(ProviderOperation.RECIPIENT_VALIDATION),
                correlation_ref=request.correlation_ref,
            ),
            valid=not errors,
            messages=tuple(messages),
            errors=tuple(errors),
        )

    def validate_address(
        self,
        request: AddressValidationRequest,
    ) -> AddressValidationResult:
        messages: list[ProviderValidationMessage] = []
        errors: list[ProviderError] = []

        if self.profile.require_postal_code and not (
            request.address.postal_code and request.address.postal_code.strip()
        ):
            messages.append(
                ProviderValidationMessage(
                    code="postal_code_required",
                    message=("Synthetic postal provider requires a postal code."),
                    level=ProviderMessageLevel.ERROR,
                    field_name="postal_code",
                )
            )
            errors.append(
                ProviderError.from_code(
                    ProviderErrorCode.ADDRESS_VALIDATION_FAILED,
                    provider_id=(self.provider.provider_id),
                    operation=(ProviderOperation.ADDRESS_VALIDATION),
                )
            )

        return AddressValidationResult(
            provider_id=self.provider.provider_id,
            execution=DryRunExecutionMetadata(
                operation=(ProviderOperation.ADDRESS_VALIDATION),
                correlation_ref=request.correlation_ref,
            ),
            valid=not errors,
            messages=tuple(messages),
            errors=tuple(errors),
        )

    def build_shipment_payload_preview(
        self,
        request: ShipmentPayloadPreviewRequest,
    ) -> ShipmentPayloadPreviewResult:
        errors: list[ProviderError] = []
        warnings = [("Synthetic contract fixture only. No provider call was performed.")]

        if request.draft.provider_id != self.provider.provider_id:
            errors.append(
                ProviderError.from_code(
                    ProviderErrorCode.INVALID_REQUEST,
                    provider_id=(self.provider.provider_id),
                    operation=(ProviderOperation.SHIPMENT_PAYLOAD_PREVIEW),
                    safe_message=("Shipment draft provider does not match the adapter."),
                )
            )
            warnings.append("Provider mismatch detected.")

        envelope = DryRunPayloadEnvelope(
            provider_id=self.provider.provider_id,
            schema_version=("synthetic_provider_payload_preview_v0_1"),
            execution=DryRunExecutionMetadata(
                operation=(ProviderOperation.SHIPMENT_PAYLOAD_PREVIEW),
                correlation_ref=request.correlation_ref,
            ),
            normalized_input_summary=(
                (
                    "shipment_id",
                    request.draft.shipment_id,
                ),
                (
                    "external_order_ref",
                    request.draft.external_order_ref,
                ),
                (
                    "recipient_ref",
                    request.draft.recipient.recipient_ref,
                ),
                (
                    "weight_kg",
                    str(request.draft.weight_kg),
                ),
            ),
            provider_payload_preview=(
                (
                    "provider_class",
                    self.profile.provider_class.value,
                ),
                (
                    "service_type",
                    self.profile.service_type,
                ),
                (
                    "destination_city",
                    request.draft.destination.city,
                ),
                (
                    "package_description",
                    request.draft.package_description,
                ),
                (
                    "weight_kg",
                    request.draft.weight_kg,
                ),
                (
                    "preview_only",
                    True,
                ),
                (
                    "live_write",
                    False,
                ),
            ),
            warnings=tuple(warnings),
        )

        return ShipmentPayloadPreviewResult(
            envelope=envelope,
            errors=tuple(errors),
        )

    def track(
        self,
        request: TrackingLookupRequest,
    ) -> TrackingLookupResult:
        errors: list[ProviderError] = []

        if request.provider_id != self.provider.provider_id:
            errors.append(
                ProviderError.from_code(
                    ProviderErrorCode.INVALID_REQUEST,
                    provider_id=(self.provider.provider_id),
                    operation=(ProviderOperation.TRACKING_LOOKUP),
                    safe_message=("Tracking request provider does not match the adapter."),
                )
            )
        elif not self.provider.supports(ProviderCapability.TRACKING):
            errors.append(
                self.unsupported_operation_error(
                    ProviderOperation.TRACKING_LOOKUP,
                    safe_message=("Synthetic provider does not support tracking lookup."),
                )
            )

        return TrackingLookupResult(
            provider_id=self.provider.provider_id,
            tracking_number=request.tracking_number,
            correlation_ref=request.correlation_ref,
            events=(),
            errors=tuple(errors),
            read_only=True,
            provider_call_performed=False,
        )


SYNTHETIC_PROVIDER_PROFILES = (
    SyntheticProviderProfile(
        provider_id="synthetic_parcel",
        display_name="Synthetic Parcel Provider",
        provider_class=SyntheticProviderClass.PARCEL,
        service_type="warehouse_to_warehouse",
        capabilities=frozenset(
            {
                ProviderCapability.CAPABILITY_DESCRIPTION,
                ProviderCapability.RECIPIENT_VALIDATION,
                ProviderCapability.ADDRESS_VALIDATION,
                ProviderCapability.SHIPMENT_PAYLOAD_PREVIEW,
                ProviderCapability.TRACKING,
            }
        ),
    ),
    SyntheticProviderProfile(
        provider_id="synthetic_postal",
        display_name="Synthetic Postal Provider",
        provider_class=SyntheticProviderClass.POSTAL,
        service_type="postal_delivery",
        capabilities=frozenset(
            {
                ProviderCapability.CAPABILITY_DESCRIPTION,
                ProviderCapability.RECIPIENT_VALIDATION,
                ProviderCapability.ADDRESS_VALIDATION,
                ProviderCapability.SHIPMENT_PAYLOAD_PREVIEW,
                ProviderCapability.TRACKING,
            }
        ),
        require_postal_code=True,
    ),
    SyntheticProviderProfile(
        provider_id="synthetic_freight",
        display_name="Synthetic Freight Provider",
        provider_class=SyntheticProviderClass.FREIGHT,
        service_type="terminal_freight",
        capabilities=frozenset(
            {
                ProviderCapability.CAPABILITY_DESCRIPTION,
                ProviderCapability.RECIPIENT_VALIDATION,
                ProviderCapability.ADDRESS_VALIDATION,
                ProviderCapability.SHIPMENT_PAYLOAD_PREVIEW,
                ProviderCapability.TRACKING,
            }
        ),
    ),
    SyntheticProviderProfile(
        provider_id="synthetic_taxi_courier",
        display_name=("Synthetic Taxi and Courier Provider"),
        provider_class=(SyntheticProviderClass.TAXI_COURIER),
        service_type="pickup_to_dropoff",
        capabilities=frozenset(
            {
                ProviderCapability.CAPABILITY_DESCRIPTION,
                ProviderCapability.RECIPIENT_VALIDATION,
                ProviderCapability.ADDRESS_VALIDATION,
                ProviderCapability.SHIPMENT_PAYLOAD_PREVIEW,
            }
        ),
    ),
)


def build_synthetic_provider_adapters() -> tuple[SyntheticProviderAdapter, ...]:
    """Build deterministic local synthetic adapters."""

    return tuple(SyntheticProviderAdapter(profile) for profile in SYNTHETIC_PROVIDER_PROFILES)


def build_synthetic_provider_registry(
    *,
    enabled: bool = True,
) -> ProviderRegistry:
    """Build a registry for local contract testing only."""

    registry = ProviderRegistry()

    for adapter in build_synthetic_provider_adapters():
        registry.register(
            adapter,
            enabled=enabled,
            source="synthetic_contract_fixture",
        )

    return registry
