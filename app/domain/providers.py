from dataclasses import dataclass, field
from enum import StrEnum


class ProviderCapability(StrEnum):
    """Provider-neutral capabilities understood by Logistics Service."""

    RECIPIENT_VALIDATION = "recipient_validation"
    ADDRESS_VALIDATION = "address_validation"
    SHIPMENT_PAYLOAD_PREVIEW = "shipment_payload_preview"
    TRACKING = "tracking"
    CAPABILITY_DESCRIPTION = "capability_description"
    LIVE_SHIPMENT_CREATION = "live_shipment_creation"


@dataclass(frozen=True, slots=True)
class LogisticsProvider:
    """Safe provider description without credentials or provider SDK objects."""

    provider_id: str
    display_name: str
    capabilities: frozenset[ProviderCapability] = field(default_factory=frozenset)
    live_write_enabled: bool = False

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("provider_id must not be empty")

        if not self.display_name.strip():
            raise ValueError("display_name must not be empty")

        if self.live_write_enabled:
            raise ValueError("Live provider writes are disabled in bootstrap checkpoint v0.1")

        if ProviderCapability.LIVE_SHIPMENT_CREATION in self.capabilities:
            raise ValueError(
                "LIVE_SHIPMENT_CREATION capability is disabled in bootstrap checkpoint v0.1"
            )

    def supports(self, capability: ProviderCapability) -> bool:
        return capability in self.capabilities
