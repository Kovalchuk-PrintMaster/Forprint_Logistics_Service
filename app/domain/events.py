from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from app.domain.tracking import (
    ShipmentEventEnvelope,
    ShipmentEventType,
    stable_contract_digest,
)

NOTIFICATION_PROJECTION_VERSION = "logistics_notification_projection_v0_1"


class LogisticsNotificationType(StrEnum):
    """Legacy local notification event types."""

    SHIPMENT_PREVIEW_READY = "shipment_preview_ready"
    TRACKING_STATUS_CHANGED = "tracking_status_changed"
    DELIVERY_COMPLETED = "delivery_completed"
    LOGISTICS_WARNING = "logistics_warning"


@dataclass(frozen=True, slots=True)
class LogisticsNotificationEvent:
    """Legacy local payload for future display surfaces."""

    event_id: str
    shipment_id: str
    event_type: LogisticsNotificationType
    occurred_at: datetime
    message: str
    attributes: tuple[
        tuple[str, str],
        ...,
    ] = field(default_factory=tuple)
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


class NotificationPriority(StrEnum):
    """Channel-neutral attention level."""

    NORMAL = "normal"
    ATTENTION = "attention"
    CRITICAL = "critical"


class NotificationProjectionType(StrEnum):
    """Notification categories derived from canonical events."""

    SHIPMENT_CREATED = "shipment_created"
    TRACKING_UPDATED = "tracking_updated"
    ARRIVED = "arrived"
    DELIVERED = "delivered"
    FAILED = "failed"
    NEEDS_ATTENTION = "needs_attention"


_EVENT_PRIORITY: dict[
    ShipmentEventType,
    NotificationPriority,
] = {
    ShipmentEventType.SHIPMENT_CREATED: (NotificationPriority.NORMAL),
    ShipmentEventType.TRACKING_UPDATED: (NotificationPriority.NORMAL),
    ShipmentEventType.ARRIVED: NotificationPriority.NORMAL,
    ShipmentEventType.DELIVERED: (NotificationPriority.NORMAL),
    ShipmentEventType.FAILED: NotificationPriority.CRITICAL,
    ShipmentEventType.NEEDS_ATTENTION: (NotificationPriority.ATTENTION),
}


@dataclass(frozen=True, slots=True)
class LogisticsNotificationProjection:
    """Channel-neutral handoff derived from a Logistics event.

    It intentionally contains no Telegram message text, buttons,
    chat state, delivery attempts or channel runtime persistence.
    """

    notification_key: str
    notification_type: NotificationProjectionType
    projection_version: str
    event_id: str
    event_type: ShipmentEventType
    event_version: str
    shipment_reference: str
    occurred_at: datetime
    priority: NotificationPriority
    correlation_id: str
    idempotency_key: str
    tracking_reference: str | None = None
    provider_id: str | None = None
    recipient_reference: str | None = None
    facts: tuple[
        tuple[str, str],
        ...,
    ] = field(default_factory=tuple)
    preview_only: bool = True
    live_write: bool = False
    provider_call_performed: bool = False
    telegram_api_call_performed: bool = False
    cross_repository_write: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "notification_type",
            NotificationProjectionType(self.notification_type),
        )
        object.__setattr__(
            self,
            "event_type",
            ShipmentEventType(self.event_type),
        )
        object.__setattr__(
            self,
            "priority",
            NotificationPriority(self.priority),
        )

        for field_name in (
            "notification_key",
            "projection_version",
            "event_id",
            "event_version",
            "shipment_reference",
            "correlation_id",
            "idempotency_key",
        ):
            value = str(getattr(self, field_name)).strip()

            if not value:
                raise ValueError(f"{field_name} must not be empty")

            object.__setattr__(
                self,
                field_name,
                value,
            )

        if self.projection_version != NOTIFICATION_PROJECTION_VERSION:
            raise ValueError("Unsupported notification projection version")

        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise ValueError("occurred_at must be timezone-aware")

        expected_type = NotificationProjectionType(self.event_type.value)

        if self.notification_type is not expected_type:
            raise ValueError("notification_type and event_type do not match")

        for field_name in (
            "tracking_reference",
            "provider_id",
            "recipient_reference",
        ):
            value = getattr(self, field_name)

            if value is not None:
                normalized = str(value).strip()

                if not normalized:
                    raise ValueError(f"{field_name} must not be empty")

                object.__setattr__(
                    self,
                    field_name,
                    normalized,
                )

        normalized_facts: list[tuple[str, str]] = []
        seen: set[str] = set()

        for raw_key, raw_value in self.facts:
            key = str(raw_key).strip()
            value = str(raw_value).strip()
            normalized_key = key.casefold()

            if not key or not value:
                raise ValueError("notification facts must not be empty")

            if normalized_key in seen:
                raise ValueError("notification fact keys must be unique")

            forbidden = (
                "telegram_message",
                "telegram_chat",
                "telegram_buttons",
                "credential",
                "password",
                "secret",
                "token",
                "raw_response",
            )

            if any(marker in normalized_key for marker in forbidden):
                raise ValueError(
                    "notification facts contain a forbidden channel or sensitive field"
                )

            seen.add(normalized_key)
            normalized_facts.append((key, value))

        object.__setattr__(
            self,
            "facts",
            tuple(
                sorted(
                    normalized_facts,
                    key=lambda item: item[0].casefold(),
                )
            ),
        )

        if not self.preview_only:
            raise ValueError("Notification projections must remain preview-only")

        if self.live_write:
            raise ValueError("Live writes are disabled")

        if self.provider_call_performed:
            raise ValueError("Real provider calls are disabled")

        if self.telegram_api_call_performed:
            raise ValueError("Telegram API calls are disabled")

        if self.cross_repository_write:
            raise ValueError("Cross-repository writes are disabled")

    @classmethod
    def from_event(
        cls,
        event: ShipmentEventEnvelope,
        *,
        recipient_reference: str | None = None,
    ) -> LogisticsNotificationProjection:
        notification_key = "notification_" + stable_contract_digest(
            NOTIFICATION_PROJECTION_VERSION,
            event.event_id,
            recipient_reference or "",
        )
        idempotency_key = "notification_idem_" + stable_contract_digest(
            event.idempotency_key,
            recipient_reference or "",
            NOTIFICATION_PROJECTION_VERSION,
        )

        facts: list[tuple[str, str]] = [
            (
                "current_state",
                event.current_state.value,
            ),
            (
                "event_type",
                event.event_type.value,
            ),
        ]

        if event.provider_event_code is not None:
            facts.append(
                (
                    "provider_event_code",
                    event.provider_event_code,
                )
            )

        facts.extend(event.details)

        return cls(
            notification_key=notification_key,
            notification_type=(NotificationProjectionType(event.event_type.value)),
            projection_version=(NOTIFICATION_PROJECTION_VERSION),
            event_id=event.event_id,
            event_type=event.event_type,
            event_version=event.event_version,
            shipment_reference=event.shipment_reference,
            tracking_reference=event.tracking_reference,
            provider_id=event.provider_id,
            occurred_at=event.occurred_at,
            recipient_reference=recipient_reference,
            facts=tuple(facts),
            priority=_EVENT_PRIORITY[event.event_type],
            correlation_id=event.correlation_id,
            idempotency_key=idempotency_key,
            preview_only=True,
            live_write=False,
            provider_call_performed=False,
            telegram_api_call_performed=False,
            cross_repository_write=False,
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "cross_repository_write": (self.cross_repository_write),
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "event_version": self.event_version,
            "facts": dict(self.facts),
            "idempotency_key": self.idempotency_key,
            "live_write": self.live_write,
            "notification_key": self.notification_key,
            "notification_type": (self.notification_type.value),
            "occurred_at": self.occurred_at.isoformat(),
            "preview_only": self.preview_only,
            "priority": self.priority.value,
            "projection_version": self.projection_version,
            "provider_call_performed": (self.provider_call_performed),
            "provider_id": self.provider_id,
            "recipient_reference": (self.recipient_reference),
            "shipment_reference": (self.shipment_reference),
            "telegram_api_call_performed": (self.telegram_api_call_performed),
            "tracking_reference": (self.tracking_reference),
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_mapping(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
