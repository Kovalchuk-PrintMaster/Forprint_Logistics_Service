from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class LogisticsNotificationType(StrEnum):
    """Notification events produced by the logistics domain."""

    SHIPMENT_PREVIEW_READY = "shipment_preview_ready"
    TRACKING_STATUS_CHANGED = "tracking_status_changed"
    DELIVERY_COMPLETED = "delivery_completed"
    LOGISTICS_WARNING = "logistics_warning"


@dataclass(frozen=True, slots=True)
class LogisticsNotificationEvent:
    """Local payload for future channel display."""

    event_id: str
    shipment_id: str
    event_type: LogisticsNotificationType
    occurred_at: datetime
    message: str
    attributes: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    local_payload: bool = True
    delivery_performed: bool = False

    def __post_init__(self) -> None:
        if not self.event_id.strip():
            raise ValueError("event_id must not be empty")

        if not self.shipment_id.strip():
            raise ValueError("shipment_id must not be empty")

        if not self.message.strip():
            raise ValueError("message must not be empty")

        if not self.local_payload:
            raise ValueError("Logistics notifications must remain local display payloads")

        if self.delivery_performed:
            raise ValueError("Telegram, CRM and Website delivery is disabled in this checkpoint")
