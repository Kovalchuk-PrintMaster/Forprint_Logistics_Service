from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ProviderOperation(StrEnum):
    """Provider-neutral operations understood by Logistics Service."""

    CAPABILITY_DESCRIPTION = "capability_description"
    RECIPIENT_VALIDATION = "recipient_validation"
    ADDRESS_VALIDATION = "address_validation"
    SHIPMENT_PAYLOAD_PREVIEW = "shipment_payload_preview"
    TRACKING_LOOKUP = "tracking_lookup"
    DELIVERY_QUOTE_LOOKUP = "delivery_quote_lookup"
    LIVE_SHIPMENT_CREATION = "live_shipment_creation"


class ProviderCapability(StrEnum):
    """Provider-neutral capabilities understood by Logistics Service."""

    RECIPIENT_VALIDATION = "recipient_validation"
    ADDRESS_VALIDATION = "address_validation"
    SHIPMENT_PAYLOAD_PREVIEW = "shipment_payload_preview"
    TRACKING = "tracking"
    CAPABILITY_DESCRIPTION = "capability_description"
    DELIVERY_QUOTE_LOOKUP = "delivery_quote_lookup"
    LIVE_SHIPMENT_CREATION = "live_shipment_creation"


OPERATION_CAPABILITIES: dict[
    ProviderOperation,
    ProviderCapability,
] = {
    ProviderOperation.CAPABILITY_DESCRIPTION: ProviderCapability.CAPABILITY_DESCRIPTION,
    ProviderOperation.RECIPIENT_VALIDATION: ProviderCapability.RECIPIENT_VALIDATION,
    ProviderOperation.ADDRESS_VALIDATION: ProviderCapability.ADDRESS_VALIDATION,
    ProviderOperation.SHIPMENT_PAYLOAD_PREVIEW: ProviderCapability.SHIPMENT_PAYLOAD_PREVIEW,
    ProviderOperation.TRACKING_LOOKUP: ProviderCapability.TRACKING,
    ProviderOperation.DELIVERY_QUOTE_LOOKUP: ProviderCapability.DELIVERY_QUOTE_LOOKUP,
    ProviderOperation.LIVE_SHIPMENT_CREATION: ProviderCapability.LIVE_SHIPMENT_CREATION,
}


@dataclass(frozen=True, slots=True)
class ProviderCapabilitySupport:
    """Deterministic supported or unsupported capability result."""

    capability: ProviderCapability
    supported: bool
    reason_code: str
    safe_message: str

    def __post_init__(self) -> None:
        if not self.reason_code.strip():
            raise ValueError("reason_code must not be empty")

        if not self.safe_message.strip():
            raise ValueError("safe_message must not be empty")


@dataclass(frozen=True, slots=True)
class LogisticsProvider:
    """Safe provider description without credentials or SDK objects."""

    provider_id: str
    display_name: str
    capabilities: frozenset[ProviderCapability] = field(default_factory=frozenset)
    live_write_enabled: bool = False

    def __post_init__(self) -> None:
        provider_id = self.provider_id.strip()
        display_name = self.display_name.strip()

        if not provider_id:
            raise ValueError("provider_id must not be empty")

        if not display_name:
            raise ValueError("display_name must not be empty")

        if self.live_write_enabled:
            raise ValueError("Live provider writes are disabled")

        if ProviderCapability.LIVE_SHIPMENT_CREATION in self.capabilities:
            raise ValueError("LIVE_SHIPMENT_CREATION capability is disabled")

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

    def supports(
        self,
        capability: ProviderCapability,
    ) -> bool:
        return capability in self.capabilities

    def capability_support(
        self,
        capability: ProviderCapability,
    ) -> ProviderCapabilitySupport:
        """Return an explicit capability discovery result."""

        if capability is ProviderCapability.LIVE_SHIPMENT_CREATION:
            return ProviderCapabilitySupport(
                capability=capability,
                supported=False,
                reason_code="live_write_disabled",
                safe_message=("Live provider shipment creation is disabled."),
            )

        if capability in self.capabilities:
            return ProviderCapabilitySupport(
                capability=capability,
                supported=True,
                reason_code="supported",
                safe_message=("Provider declares this capability."),
            )

        return ProviderCapabilitySupport(
            capability=capability,
            supported=False,
            reason_code="unsupported_capability",
            safe_message=("Provider does not declare this capability."),
        )

    def operation_support(
        self,
        operation: ProviderOperation,
    ) -> ProviderCapabilitySupport:
        """Resolve provider support for a typed operation."""

        return self.capability_support(OPERATION_CAPABILITIES[operation])

    def describe_capabilities(
        self,
    ) -> tuple[ProviderCapabilitySupport, ...]:
        """Return deterministic discovery for every capability."""

        return tuple(
            self.capability_support(capability)
            for capability in sorted(
                ProviderCapability,
                key=lambda item: item.value,
            )
        )
