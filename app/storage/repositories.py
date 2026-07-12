from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.domain import (
    LogisticsNotificationEvent,
    LogisticsProvider,
    RecipientRef,
    ShipmentDraft,
    TrackingEvent,
    TrackingRequest,
)


@runtime_checkable
class LogisticsRepository(Protocol):
    """Provider-neutral local persistence boundary."""

    def save_provider(
        self,
        provider: LogisticsProvider,
    ) -> LogisticsProvider:
        """Save or replace provider metadata."""

    def get_provider(
        self,
        provider_id: str,
    ) -> LogisticsProvider | None:
        """Return provider metadata."""

    def list_providers(
        self,
    ) -> tuple[LogisticsProvider, ...]:
        """Return all local providers."""

    def save_recipient(
        self,
        recipient: RecipientRef,
    ) -> RecipientRef:
        """Save a non-canonical recipient reference."""

    def get_recipient(
        self,
        recipient_ref: str,
    ) -> RecipientRef | None:
        """Return a recipient reference."""

    def list_recipients(
        self,
    ) -> tuple[RecipientRef, ...]:
        """Return all recipient references."""

    def save_shipment_draft(
        self,
        draft: ShipmentDraft,
    ) -> ShipmentDraft:
        """Save a preview-only shipment draft."""

    def get_shipment_draft(
        self,
        shipment_id: str,
    ) -> ShipmentDraft | None:
        """Return a shipment draft."""

    def list_shipment_drafts(
        self,
    ) -> tuple[ShipmentDraft, ...]:
        """Return all shipment drafts."""

    def save_tracking_request(
        self,
        request: TrackingRequest,
    ) -> TrackingRequest:
        """Save a local-only tracking request."""

    def get_tracking_request(
        self,
        provider_id: str,
        tracking_number: str,
    ) -> TrackingRequest | None:
        """Return a local tracking request."""

    def list_tracking_requests(
        self,
    ) -> tuple[TrackingRequest, ...]:
        """Return all local tracking requests."""

    def save_tracking_event(
        self,
        event: TrackingEvent,
    ) -> TrackingEvent:
        """Save a local tracking event."""

    def get_tracking_event(
        self,
        event_id: str,
    ) -> TrackingEvent | None:
        """Return a tracking event."""

    def list_tracking_events(
        self,
        *,
        provider_id: str | None = None,
        tracking_number: str | None = None,
    ) -> tuple[TrackingEvent, ...]:
        """Return optionally filtered tracking events."""

    def save_notification_event(
        self,
        event: LogisticsNotificationEvent,
    ) -> LogisticsNotificationEvent:
        """Save a local display payload."""

    def get_notification_event(
        self,
        event_id: str,
    ) -> LogisticsNotificationEvent | None:
        """Return a notification payload."""

    def list_notification_events(
        self,
        *,
        shipment_id: str | None = None,
    ) -> tuple[LogisticsNotificationEvent, ...]:
        """Return optionally filtered notifications."""
