from dataclasses import dataclass
from datetime import datetime

from app.domain.shipments import ShipmentStatus


@dataclass(frozen=True, slots=True)
class TrackingRequest:
    """Provider-neutral request to read current shipment tracking state."""

    provider_id: str
    tracking_number: str
    requested_at: datetime

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("provider_id must not be empty")

        if not self.tracking_number.strip():
            raise ValueError("tracking_number must not be empty")


@dataclass(frozen=True, slots=True)
class TrackingEvent:
    """Normalized tracking event with the provider's original status retained."""

    event_id: str
    provider_id: str
    tracking_number: str
    occurred_at: datetime
    normalized_status: ShipmentStatus
    provider_status: str
    description: str | None = None

    def __post_init__(self) -> None:
        if not self.event_id.strip():
            raise ValueError("event_id must not be empty")

        if not self.provider_status.strip():
            raise ValueError("provider_status must not be empty")
