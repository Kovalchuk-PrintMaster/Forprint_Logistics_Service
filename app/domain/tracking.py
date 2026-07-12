from dataclasses import dataclass
from datetime import datetime

from app.domain.shipments import ShipmentStatus


@dataclass(frozen=True, slots=True)
class TrackingRequest:
    """Local request representing future tracking intent."""

    provider_id: str
    tracking_number: str
    requested_at: datetime
    local_only: bool = True
    provider_call_performed: bool = False

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("provider_id must not be empty")

        if not self.tracking_number.strip():
            raise ValueError("tracking_number must not be empty")

        if not self.local_only:
            raise ValueError("Tracking requests must remain local-only")

        if self.provider_call_performed:
            raise ValueError("Provider tracking calls are disabled in this checkpoint")


@dataclass(frozen=True, slots=True)
class TrackingEvent:
    """Provider-neutral local tracking event."""

    event_id: str
    provider_id: str
    tracking_number: str
    occurred_at: datetime
    normalized_status: ShipmentStatus
    provider_status: str
    description: str | None = None
    local_record: bool = True

    def __post_init__(self) -> None:
        if not self.event_id.strip():
            raise ValueError("event_id must not be empty")

        if not self.provider_id.strip():
            raise ValueError("provider_id must not be empty")

        if not self.tracking_number.strip():
            raise ValueError("tracking_number must not be empty")

        if not self.provider_status.strip():
            raise ValueError("provider_status must not be empty")

        if not self.local_record:
            raise ValueError("Tracking events must remain local records")
