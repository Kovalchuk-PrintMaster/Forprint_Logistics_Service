from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import NoReturn, final

from app.domain.providers import LogisticsProvider, ProviderCapability
from app.domain.recipients import AddressSnapshot, RecipientRef
from app.domain.shipments import ShipmentDraft
from app.domain.tracking import TrackingEvent, TrackingRequest


class LiveProviderWriteDisabledError(RuntimeError):
    """Raised whenever code attempts a provider mutation in a safe checkpoint."""


class ProviderAdapter(ABC):
    """Provider-neutral adapter boundary.

    Current implementations may validate data, build payload previews and read
    tracking information. Provider-side shipment creation is intentionally
    disabled.
    """

    @property
    @abstractmethod
    def provider(self) -> LogisticsProvider:
        """Return provider metadata without exposing credentials."""

    @abstractmethod
    def validate_recipient(
        self,
        recipient: RecipientRef,
        address: AddressSnapshot,
    ) -> tuple[str, ...]:
        """Return validation messages. An empty tuple means no problems."""

    @abstractmethod
    def build_shipment_payload_preview(
        self,
        draft: ShipmentDraft,
    ) -> Mapping[str, object]:
        """Build a non-mutating provider payload preview."""

    @abstractmethod
    def track(self, request: TrackingRequest) -> Sequence[TrackingEvent]:
        """Read or normalize provider tracking information."""

    def describe_capabilities(self) -> tuple[ProviderCapability, ...]:
        return tuple(sorted(self.provider.capabilities, key=str))

    @final
    def create_shipment(self, draft: ShipmentDraft) -> NoReturn:
        """Reject all live provider shipment creation in bootstrap v0.1."""

        del draft

        raise LiveProviderWriteDisabledError(
            "Live provider shipment creation is disabled. "
            "A future approved checkpoint must add dry-run controls, "
            "manual confirmation, environment safety checks and audit records."
        )
