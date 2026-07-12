from dataclasses import dataclass, field
from enum import StrEnum

from app.domain.recipients import (
    AddressSnapshot,
    RecipientRef,
)


class ShipmentStatus(StrEnum):
    """Provider-neutral local shipment lifecycle status."""

    DRAFT = "draft"
    DRAFT_CREATED = "draft_created"
    PREVIEW_READY = "preview_ready"
    TRACKING_REQUESTED = "tracking_requested"
    TRACKING = "tracking"
    TRACKING_UPDATED = "tracking_updated"
    ARRIVED = "arrived"
    DELIVERED = "delivered"
    FAILED = "failed"
    NEEDS_ATTENTION = "needs_attention"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class ShipmentDraft:
    """Local preview draft that is never written to a provider."""

    shipment_id: str
    external_order_ref: str
    provider_id: str
    recipient: RecipientRef
    destination: AddressSnapshot
    package_description: str
    weight_kg: float
    status: ShipmentStatus = ShipmentStatus.DRAFT
    metadata: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    preview_only: bool = True
    live_provider_write: bool = False

    def __post_init__(self) -> None:
        if not self.shipment_id.strip():
            raise ValueError("shipment_id must not be empty")

        if not self.external_order_ref.strip():
            raise ValueError("external_order_ref must not be empty")

        if not self.provider_id.strip():
            raise ValueError("provider_id must not be empty")

        if not self.package_description.strip():
            raise ValueError("package_description must not be empty")

        if self.weight_kg <= 0:
            raise ValueError("weight_kg must be greater than zero")

        if not self.recipient.non_canonical:
            raise ValueError("Shipment drafts require a non-canonical recipient reference")

        if not self.destination.shipment_time_snapshot:
            raise ValueError("Shipment drafts require a shipment-time address snapshot")

        if not self.preview_only:
            raise ValueError("Shipment drafts must remain preview-only")

        if self.live_provider_write:
            raise ValueError("Live provider writes are disabled")
