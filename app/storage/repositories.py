from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.domain import (
    LogisticsNotificationEvent,
    LogisticsProvider,
    RecipientRef,
    ShipmentDraft,
    TrackingEvent,
)


@runtime_checkable
class LogisticsRepository(Protocol):
    """Provider-neutral local persistence boundary.

    Implementations in the current checkpoint must remain local and
    must not perform provider API calls or claim production database
    ownership.
    """

    def save_provider(
        self,
        provider: LogisticsProvider,
    ) -> LogisticsProvider:
        """Save or replace local provider metadata."""

    def get_provider(
        self,
        provider_id: str,
    ) -> LogisticsProvider | None:
        """Return provider metadata by local identifier."""

    def list_providers(
        self,
    ) -> tuple[LogisticsProvider, ...]:
        """Return all locally stored providers."""

    def save_recipient(
        self,
        recipient: RecipientRef,
    ) -> RecipientRef:
        """Save or replace a non-canonical recipient reference."""

    def get_recipient(
        self,
        recipient_ref: str,
    ) -> RecipientRef | None:
        """Return a non-canonical recipient reference."""

    def list_recipients(
        self,
    ) -> tuple[RecipientRef, ...]:
        """Return all locally stored recipient references."""

    def save_shipment_draft(
        self,
        draft: ShipmentDraft,
    ) -> ShipmentDraft:
        """Save or replace a preview-only shipment draft."""

    def get_shipment_draft(
        self,
        shipment_id: str,
    ) -> ShipmentDraft | None:
        """Return a local shipment draft."""

    def list_shipment_drafts(
        self,
    ) -> tuple[ShipmentDraft, ...]:
        """Return all locally stored shipment drafts."""

    def save_tracking_event(
        self,
        event: TrackingEvent,
    ) -> TrackingEvent:
        """Save or replace a local tracking event."""

    def get_tracking_event(
        self,
        event_id: str,
    ) -> TrackingEvent | None:
        """Return a local tracking event."""

    def list_tracking_events(
        self,
        *,
        provider_id: str | None = None,
        tracking_number: str | None = None,
    ) -> tuple[TrackingEvent, ...]:
        """Return tracking events with optional local filtering."""

    def save_notification_event(
        self,
        event: LogisticsNotificationEvent,
    ) -> LogisticsNotificationEvent:
        """Save or replace a local notification payload."""

    def get_notification_event(
        self,
        event_id: str,
    ) -> LogisticsNotificationEvent | None:
        """Return a local notification payload."""

    def list_notification_events(
        self,
        *,
        shipment_id: str | None = None,
    ) -> tuple[LogisticsNotificationEvent, ...]:
        """Return notification events with optional filtering."""
