from __future__ import annotations

from datetime import datetime

from app.domain import (
    LogisticsNotificationEvent,
    LogisticsNotificationType,
)
from app.services.errors import LocalModelSafetyError
from app.storage import LogisticsRepository


class NotificationEventService:
    """Create local payloads for future display surfaces."""

    def __init__(
        self,
        repository: LogisticsRepository,
    ) -> None:
        self._repository = repository

    def create_local_payload(
        self,
        *,
        event_id: str,
        shipment_id: str,
        event_type: LogisticsNotificationType,
        occurred_at: datetime,
        message: str,
        attributes: tuple[
            tuple[str, str],
            ...,
        ] = (),
    ) -> LogisticsNotificationEvent:
        event = LogisticsNotificationEvent(
            event_id=event_id,
            shipment_id=shipment_id,
            event_type=event_type,
            occurred_at=occurred_at,
            message=message,
            attributes=attributes,
            local_payload=True,
            delivery_performed=False,
        )

        if not event.local_payload or event.delivery_performed:
            raise LocalModelSafetyError("Unsafe notification event state")

        return self._repository.save_notification_event(event)
