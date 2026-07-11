from dataclasses import dataclass, field
from enum import StrEnum

from app.domain.recipients import AddressSnapshot, RecipientRef


class ShipmentStatus(StrEnum):
    """Provider-neutral shipment lifecycle status."""

    DRAFT = "draft"
    PREVIEW_READY = "preview_ready"
    TRACKING = "tracking"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class ShipmentDraft:
    """A local shipment draft that has not been written to a provider."""

    shipment_id: str
    external_order_ref: str
    provider_id: str
    recipient: RecipientRef
    destination: AddressSnapshot
    package_description: str
    weight_kg: float
    status: ShipmentStatus = ShipmentStatus.DRAFT
    metadata: tuple[tuple[str, str], ...] = field(default_factory=tuple)

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
