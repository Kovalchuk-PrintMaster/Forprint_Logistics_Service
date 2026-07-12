from __future__ import annotations

from datetime import datetime

from app.domain import (
    ShipmentStatus,
    TrackingEvent,
    TrackingRequest,
)
from app.services.errors import LocalModelSafetyError
from app.storage import LogisticsRepository


class TrackingEventService:
    """Create local requests and record local tracking events."""

    def __init__(
        self,
        repository: LogisticsRepository,
    ) -> None:
        self._repository = repository

    def create_local_request(
        self,
        *,
        provider_id: str,
        tracking_number: str,
        requested_at: datetime,
    ) -> TrackingRequest:
        request = TrackingRequest(
            provider_id=provider_id,
            tracking_number=tracking_number,
            requested_at=requested_at,
            local_only=True,
            provider_call_performed=False,
        )

        if not request.local_only or request.provider_call_performed:
            raise LocalModelSafetyError("Unsafe tracking request state")

        return self._repository.save_tracking_request(request)

    def record_local_event(
        self,
        *,
        event_id: str,
        provider_id: str,
        tracking_number: str,
        occurred_at: datetime,
        normalized_status: ShipmentStatus,
        provider_status: str,
        description: str | None = None,
    ) -> TrackingEvent:
        event = TrackingEvent(
            event_id=event_id,
            provider_id=provider_id,
            tracking_number=tracking_number,
            occurred_at=occurred_at,
            normalized_status=normalized_status,
            provider_status=provider_status,
            description=description,
            local_record=True,
        )

        if not event.local_record:
            raise LocalModelSafetyError("Tracking event must remain local")

        return self._repository.save_tracking_event(event)
