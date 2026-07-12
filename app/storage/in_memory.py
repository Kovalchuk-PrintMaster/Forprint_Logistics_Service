from __future__ import annotations

from app.domain import (
    LogisticsNotificationEvent,
    LogisticsProvider,
    RecipientRef,
    ShipmentDraft,
    TrackingEvent,
)


class RepositoryReferenceError(ValueError):
    """Raised when a local draft references unknown repository data."""


class InMemoryLogisticsRepository:
    """Safe in-memory implementation of the logistics repository.

    Data exists only for the lifetime of this Python object. The
    repository performs no filesystem, database or provider API writes.
    """

    def __init__(self) -> None:
        self._providers: dict[str, LogisticsProvider] = {}
        self._recipients: dict[str, RecipientRef] = {}
        self._shipment_drafts: dict[str, ShipmentDraft] = {}
        self._tracking_events: dict[str, TrackingEvent] = {}
        self._notification_events: dict[
            str,
            LogisticsNotificationEvent,
        ] = {}

    def save_provider(
        self,
        provider: LogisticsProvider,
    ) -> LogisticsProvider:
        self._providers[provider.provider_id] = provider
        return provider

    def get_provider(
        self,
        provider_id: str,
    ) -> LogisticsProvider | None:
        return self._providers.get(provider_id)

    def list_providers(
        self,
    ) -> tuple[LogisticsProvider, ...]:
        return tuple(self._providers.values())

    def save_recipient(
        self,
        recipient: RecipientRef,
    ) -> RecipientRef:
        self._recipients[recipient.recipient_ref] = recipient
        return recipient

    def get_recipient(
        self,
        recipient_ref: str,
    ) -> RecipientRef | None:
        return self._recipients.get(recipient_ref)

    def list_recipients(
        self,
    ) -> tuple[RecipientRef, ...]:
        return tuple(self._recipients.values())

    def save_shipment_draft(
        self,
        draft: ShipmentDraft,
    ) -> ShipmentDraft:
        if draft.provider_id not in self._providers:
            raise RepositoryReferenceError(
                f"Shipment draft references an unknown provider: {draft.provider_id}"
            )

        recipient_ref = draft.recipient.recipient_ref

        if recipient_ref not in self._recipients:
            raise RepositoryReferenceError(
                f"Shipment draft references an unknown recipient: {recipient_ref}"
            )

        self._shipment_drafts[draft.shipment_id] = draft
        return draft

    def get_shipment_draft(
        self,
        shipment_id: str,
    ) -> ShipmentDraft | None:
        return self._shipment_drafts.get(shipment_id)

    def list_shipment_drafts(
        self,
    ) -> tuple[ShipmentDraft, ...]:
        return tuple(self._shipment_drafts.values())

    def save_tracking_event(
        self,
        event: TrackingEvent,
    ) -> TrackingEvent:
        self._tracking_events[event.event_id] = event
        return event

    def get_tracking_event(
        self,
        event_id: str,
    ) -> TrackingEvent | None:
        return self._tracking_events.get(event_id)

    def list_tracking_events(
        self,
        *,
        provider_id: str | None = None,
        tracking_number: str | None = None,
    ) -> tuple[TrackingEvent, ...]:
        events = self._tracking_events.values()

        return tuple(
            event
            for event in events
            if (provider_id is None or event.provider_id == provider_id)
            and (tracking_number is None or event.tracking_number == tracking_number)
        )

    def save_notification_event(
        self,
        event: LogisticsNotificationEvent,
    ) -> LogisticsNotificationEvent:
        self._notification_events[event.event_id] = event
        return event

    def get_notification_event(
        self,
        event_id: str,
    ) -> LogisticsNotificationEvent | None:
        return self._notification_events.get(event_id)

    def list_notification_events(
        self,
        *,
        shipment_id: str | None = None,
    ) -> tuple[LogisticsNotificationEvent, ...]:
        events = self._notification_events.values()

        return tuple(
            event for event in events if (shipment_id is None or event.shipment_id == shipment_id)
        )
