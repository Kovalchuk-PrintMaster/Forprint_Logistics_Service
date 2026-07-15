from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.domain.provider_errors import (
    ProviderError,
    is_sensitive_key,
)
from app.domain.providers import (
    LogisticsProvider,
    ProviderCapability,
    ProviderCapabilitySupport,
    ProviderOperation,
)
from app.domain.recipients import (
    AddressSnapshot,
    RecipientRef,
)
from app.domain.shipments import ShipmentDraft
from app.domain.tracking import TrackingEvent


class ProviderMessageLevel(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ProviderValidationMessage:
    code: str
    message: str
    level: ProviderMessageLevel
    field_name: str | None = None

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("validation message code must not be empty")

        if not self.message.strip():
            raise ValueError("validation message must not be empty")


@dataclass(frozen=True, slots=True)
class DryRunExecutionMetadata:
    operation: ProviderOperation
    correlation_ref: str
    preview_only: bool = True
    live_write: bool = False
    provider_call_performed: bool = False

    def __post_init__(self) -> None:
        if not self.correlation_ref.strip():
            raise ValueError("correlation_ref must not be empty")

        if not self.preview_only:
            raise ValueError("Provider contract execution must remain preview-only")

        if self.live_write:
            raise ValueError("Live provider writes are disabled")

        if self.provider_call_performed:
            raise ValueError("Real provider calls are disabled")


@dataclass(frozen=True, slots=True)
class RecipientValidationRequest:
    correlation_ref: str
    recipient: RecipientRef
    address: AddressSnapshot

    def __post_init__(self) -> None:
        if not self.correlation_ref.strip():
            raise ValueError("correlation_ref must not be empty")

        if not self.recipient.non_canonical:
            raise ValueError("Recipient reference must remain non-canonical")

        if not self.address.shipment_time_snapshot:
            raise ValueError("Address must remain a shipment-time snapshot")


@dataclass(frozen=True, slots=True)
class AddressValidationRequest:
    correlation_ref: str
    address: AddressSnapshot

    def __post_init__(self) -> None:
        if not self.correlation_ref.strip():
            raise ValueError("correlation_ref must not be empty")

        if not self.address.shipment_time_snapshot:
            raise ValueError("Address must remain a shipment-time snapshot")


@dataclass(frozen=True, slots=True)
class ShipmentPayloadPreviewRequest:
    correlation_ref: str
    draft: ShipmentDraft
    schema_version: str = "provider_shipment_preview_request_v0_1"

    def __post_init__(self) -> None:
        if not self.correlation_ref.strip():
            raise ValueError("correlation_ref must not be empty")

        if not self.schema_version.strip():
            raise ValueError("schema_version must not be empty")

        if not self.draft.preview_only or self.draft.live_provider_write:
            raise ValueError("Shipment request must remain preview-only")


@dataclass(frozen=True, slots=True)
class TrackingLookupRequest:
    provider_id: str
    tracking_number: str
    correlation_ref: str
    read_only: bool = True
    provider_call_performed: bool = False

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("provider_id must not be empty")

        if not self.tracking_number.strip():
            raise ValueError("tracking_number must not be empty")

        if not self.correlation_ref.strip():
            raise ValueError("correlation_ref must not be empty")

        if not self.read_only:
            raise ValueError("Tracking lookup must remain read-only")

        if self.provider_call_performed:
            raise ValueError("Real provider calls are disabled")


@dataclass(frozen=True, slots=True)
class ProviderCapabilityDescription:
    provider_id: str
    capabilities: tuple[
        ProviderCapabilitySupport,
        ...,
    ]

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("provider_id must not be empty")

        capability_values = [item.capability for item in self.capabilities]

        if len(capability_values) != len(set(capability_values)):
            raise ValueError("Capability description contains duplicate capabilities")

        ordered = tuple(
            sorted(
                self.capabilities,
                key=lambda item: item.capability.value,
            )
        )

        object.__setattr__(
            self,
            "provider_id",
            self.provider_id.strip(),
        )
        object.__setattr__(
            self,
            "capabilities",
            ordered,
        )

    @classmethod
    def from_provider(
        cls,
        provider: LogisticsProvider,
    ) -> ProviderCapabilityDescription:
        return cls(
            provider_id=provider.provider_id,
            capabilities=(provider.describe_capabilities()),
        )

    def support_for(
        self,
        capability: ProviderCapability,
    ) -> ProviderCapabilitySupport:
        for item in self.capabilities:
            if item.capability is capability:
                return item

        return ProviderCapabilitySupport(
            capability=capability,
            supported=False,
            reason_code=("capability_not_described"),
            safe_message=("Capability is not present in the provider description."),
        )


@dataclass(frozen=True, slots=True)
class RecipientValidationResult:
    provider_id: str
    execution: DryRunExecutionMetadata
    valid: bool
    messages: tuple[
        ProviderValidationMessage,
        ...,
    ] = field(default_factory=tuple)
    errors: tuple[ProviderError, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("provider_id must not be empty")

        if self.execution.operation is not ProviderOperation.RECIPIENT_VALIDATION:
            raise ValueError("Recipient validation result uses the wrong operation")

        if self.valid and self.errors:
            raise ValueError("A valid result must not contain errors")


@dataclass(frozen=True, slots=True)
class AddressValidationResult:
    provider_id: str
    execution: DryRunExecutionMetadata
    valid: bool
    messages: tuple[
        ProviderValidationMessage,
        ...,
    ] = field(default_factory=tuple)
    errors: tuple[ProviderError, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("provider_id must not be empty")

        if self.execution.operation is not ProviderOperation.ADDRESS_VALIDATION:
            raise ValueError("Address validation result uses the wrong operation")

        if self.valid and self.errors:
            raise ValueError("A valid result must not contain errors")


def _validate_safe_items(
    items: tuple[tuple[str, Any], ...],
    *,
    field_name: str,
) -> None:
    seen: set[str] = set()

    for key, _value in items:
        normalized_key = key.strip().casefold()

        if not normalized_key:
            raise ValueError(f"{field_name} key must not be empty")

        if normalized_key in seen:
            raise ValueError(f"{field_name} keys must be unique")

        if is_sensitive_key(normalized_key):
            raise ValueError(f"{field_name} must not expose sensitive provider values")

        seen.add(normalized_key)


@dataclass(frozen=True, slots=True)
class DeliveryQuoteLookupRequest:
    """Provider-neutral future quote lookup request."""

    provider_id: str
    execution: DryRunExecutionMetadata
    normalized_input_summary: tuple[
        tuple[str, str],
        ...,
    ] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("provider_id must not be empty")

        if self.execution.operation is not ProviderOperation.DELIVERY_QUOTE_LOOKUP:
            raise ValueError("Delivery quote request uses the wrong operation")

        _validate_safe_items(
            self.normalized_input_summary,
            field_name="normalized_input_summary",
        )

        object.__setattr__(
            self,
            "provider_id",
            self.provider_id.strip(),
        )


@dataclass(frozen=True, slots=True)
class DryRunPayloadEnvelope:
    provider_id: str
    schema_version: str
    execution: DryRunExecutionMetadata
    normalized_input_summary: tuple[
        tuple[str, str],
        ...,
    ]
    provider_payload_preview: tuple[
        tuple[str, Any],
        ...,
    ]
    validation_messages: tuple[
        ProviderValidationMessage,
        ...,
    ] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    generated_artifacts: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("provider_id must not be empty")

        if not self.schema_version.strip():
            raise ValueError("schema_version must not be empty")

        _validate_safe_items(
            self.normalized_input_summary,
            field_name="normalized_input_summary",
        )
        _validate_safe_items(
            self.provider_payload_preview,
            field_name="provider_payload_preview",
        )

        for warning in self.warnings:
            if not warning.strip():
                raise ValueError("warnings must not contain empty values")

        for path in self.generated_artifacts:
            if not path.strip():
                raise ValueError("generated_artifacts must not contain empty paths")

    @property
    def operation(self) -> ProviderOperation:
        return self.execution.operation

    @property
    def correlation_ref(self) -> str:
        return self.execution.correlation_ref

    @property
    def preview_only(self) -> bool:
        return self.execution.preview_only

    @property
    def live_write(self) -> bool:
        return self.execution.live_write

    def payload_mapping(self) -> dict[str, Any]:
        return dict(self.provider_payload_preview)


@dataclass(frozen=True, slots=True)
class ShipmentPayloadPreviewResult:
    envelope: DryRunPayloadEnvelope
    errors: tuple[ProviderError, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.envelope.operation is not ProviderOperation.SHIPMENT_PAYLOAD_PREVIEW:
            raise ValueError("Shipment preview result uses the wrong operation")

    @property
    def successful(self) -> bool:
        return not self.errors


@dataclass(frozen=True, slots=True)
class DeliveryQuoteLookupResult:
    """Read-only provider-neutral quote lookup result."""

    provider_id: str
    execution: DryRunExecutionMetadata
    available: bool
    service_options: tuple[
        tuple[tuple[str, str], ...],
        ...,
    ] = field(default_factory=tuple)
    errors: tuple[ProviderError, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("provider_id must not be empty")

        if self.execution.operation is not ProviderOperation.DELIVERY_QUOTE_LOOKUP:
            raise ValueError("Delivery quote result uses the wrong operation")

        if self.available and self.errors:
            raise ValueError("An available quote result must not contain errors")

        if not self.available and self.service_options:
            raise ValueError("An unavailable quote result must not contain service options")

        for option in self.service_options:
            _validate_safe_items(
                option,
                field_name="service_option",
            )

        object.__setattr__(
            self,
            "provider_id",
            self.provider_id.strip(),
        )


@dataclass(frozen=True, slots=True)
class TrackingLookupResult:
    provider_id: str
    tracking_number: str
    correlation_ref: str
    events: tuple[TrackingEvent, ...] = field(default_factory=tuple)
    errors: tuple[ProviderError, ...] = field(default_factory=tuple)
    read_only: bool = True
    provider_call_performed: bool = False

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("provider_id must not be empty")

        if not self.tracking_number.strip():
            raise ValueError("tracking_number must not be empty")

        if not self.correlation_ref.strip():
            raise ValueError("correlation_ref must not be empty")

        if not self.read_only:
            raise ValueError("Tracking result must remain read-only")

        if self.provider_call_performed:
            raise ValueError("Real provider calls are disabled")

        for event in self.events:
            if event.provider_id != self.provider_id:
                raise ValueError("Tracking event provider mismatch")

            if event.tracking_number != self.tracking_number:
                raise ValueError("Tracking event reference mismatch")
