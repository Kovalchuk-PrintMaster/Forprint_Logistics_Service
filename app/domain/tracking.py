from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from app.domain.shipments import ShipmentStatus

TRACKING_EVENT_SCHEMA_VERSION = "tracking_event_v0_1"
SUPPORTED_TRACKING_EVENT_VERSIONS = frozenset(
    {
        TRACKING_EVENT_SCHEMA_VERSION,
    }
)

_SENSITIVE_FIELD_MARKERS = (
    "access_token",
    "api_key",
    "api_token",
    "authorization",
    "credential",
    "password",
    "raw_response",
    "secret",
    "token",
)


def _require_non_empty(
    value: str,
    *,
    field_name: str,
) -> str:
    normalized = value.strip()

    if not normalized:
        raise ValueError(f"{field_name} must not be empty")

    return normalized


def _require_timezone_aware(
    value: datetime,
    *,
    field_name: str,
) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


def _is_sensitive_key(value: str) -> bool:
    normalized = value.strip().casefold().replace("-", "_")

    return any(marker in normalized for marker in _SENSITIVE_FIELD_MARKERS)


def _normalize_safe_pairs(
    values: tuple[tuple[str, str], ...],
    *,
    field_name: str,
) -> tuple[tuple[str, str], ...]:
    normalized: list[tuple[str, str]] = []
    seen: set[str] = set()

    for raw_key, raw_value in values:
        key = _require_non_empty(
            str(raw_key),
            field_name=f"{field_name} key",
        )
        value = _require_non_empty(
            str(raw_value),
            field_name=f"{field_name} value",
        )
        normalized_key = key.casefold()

        if normalized_key in seen:
            raise ValueError(f"{field_name} keys must be unique")

        if _is_sensitive_key(normalized_key):
            raise ValueError(f"{field_name} must not expose sensitive values")

        seen.add(normalized_key)
        normalized.append((key, value))

    return tuple(
        sorted(
            normalized,
            key=lambda item: item[0].casefold(),
        )
    )


def stable_contract_digest(
    *values: object,
    length: int = 24,
) -> str:
    canonical = "\x1f".join(str(value).strip() for value in values)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:length]


class ShipmentEventType(StrEnum):
    """Canonical provider-neutral shipment event taxonomy."""

    SHIPMENT_CREATED = "shipment_created"
    TRACKING_UPDATED = "tracking_updated"
    ARRIVED = "arrived"
    DELIVERED = "delivered"
    FAILED = "failed"
    NEEDS_ATTENTION = "needs_attention"


EVENT_CURRENT_STATE: dict[
    ShipmentEventType,
    ShipmentStatus,
] = {
    ShipmentEventType.SHIPMENT_CREATED: (ShipmentStatus.DRAFT_CREATED),
    ShipmentEventType.TRACKING_UPDATED: (ShipmentStatus.TRACKING_UPDATED),
    ShipmentEventType.ARRIVED: ShipmentStatus.ARRIVED,
    ShipmentEventType.DELIVERED: ShipmentStatus.DELIVERED,
    ShipmentEventType.FAILED: ShipmentStatus.FAILED,
    ShipmentEventType.NEEDS_ATTENTION: (ShipmentStatus.NEEDS_ATTENTION),
}


TERMINAL_SHIPMENT_STATES = frozenset(
    {
        ShipmentStatus.DELIVERED,
        ShipmentStatus.FAILED,
        ShipmentStatus.CANCELLED,
    }
)


class TrackingProcessingDecision(StrEnum):
    """Deterministic event-ingestion decision."""

    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"
    OUT_OF_ORDER = "out_of_order"
    INVALID_TRANSITION = "invalid_transition"
    TERMINAL_STATE = "terminal_state"


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
    """Legacy provider-neutral local tracking record.

    This model remains available for the accepted local-model and
    provider-adapter contracts. New cross-module event handoffs use
    ShipmentEventEnvelope.
    """

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


@dataclass(frozen=True, slots=True)
class ProviderTrackingObservation:
    """Typed safe provider or synthetic tracking observation."""

    shipment_reference: str
    provider_id: str
    provider_status: str
    occurred_at: datetime
    tracking_reference: str | None = None
    provider_event_code: str | None = None
    safe_metadata: tuple[
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
            "shipment_reference",
            _require_non_empty(
                self.shipment_reference,
                field_name="shipment_reference",
            ),
        )
        object.__setattr__(
            self,
            "provider_id",
            _require_non_empty(
                self.provider_id,
                field_name="provider_id",
            ),
        )
        object.__setattr__(
            self,
            "provider_status",
            _require_non_empty(
                self.provider_status,
                field_name="provider_status",
            ),
        )
        _require_timezone_aware(
            self.occurred_at,
            field_name="occurred_at",
        )

        if self.tracking_reference is not None:
            object.__setattr__(
                self,
                "tracking_reference",
                _require_non_empty(
                    self.tracking_reference,
                    field_name="tracking_reference",
                ),
            )

        if self.provider_event_code is not None:
            object.__setattr__(
                self,
                "provider_event_code",
                _require_non_empty(
                    self.provider_event_code,
                    field_name="provider_event_code",
                ),
            )

        object.__setattr__(
            self,
            "safe_metadata",
            _normalize_safe_pairs(
                self.safe_metadata,
                field_name="safe_metadata",
            ),
        )

        if not self.preview_only:
            raise ValueError("Tracking observations must remain preview-only")

        if self.live_write:
            raise ValueError("Live writes are disabled")

        if self.provider_call_performed:
            raise ValueError("Real provider calls are disabled")

        if self.telegram_api_call_performed:
            raise ValueError("Telegram API calls are disabled")

        if self.cross_repository_write:
            raise ValueError("Cross-repository writes are disabled")

    @property
    def logical_fingerprint(self) -> str:
        metadata = "|".join(f"{key}={value}" for key, value in self.safe_metadata)

        return stable_contract_digest(
            self.shipment_reference,
            self.tracking_reference or "",
            self.provider_id,
            self.provider_event_code or "",
            self.provider_status,
            self.occurred_at.isoformat(),
            metadata,
        )


@dataclass(frozen=True, slots=True)
class ShipmentEventEnvelope:
    """Typed versioned provider-neutral shipment event."""

    event_id: str
    event_type: ShipmentEventType
    event_version: str
    occurred_at: datetime
    shipment_reference: str
    current_state: ShipmentStatus
    correlation_id: str
    idempotency_key: str
    source: str
    safe_summary: str
    recorded_at: datetime | None = None
    tracking_reference: str | None = None
    provider_id: str | None = None
    provider_event_code: str | None = None
    previous_state: ShipmentStatus | None = None
    causation_id: str | None = None
    details: tuple[
        tuple[str, str],
        ...,
    ] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    preview_only: bool = True
    live_write: bool = False
    provider_call_performed: bool = False
    telegram_api_call_performed: bool = False
    cross_repository_write: bool = False

    def __post_init__(self) -> None:
        event_type = ShipmentEventType(self.event_type)
        current_state = ShipmentStatus(self.current_state)
        previous_state = (
            ShipmentStatus(self.previous_state) if self.previous_state is not None else None
        )

        object.__setattr__(
            self,
            "event_type",
            event_type,
        )
        object.__setattr__(
            self,
            "current_state",
            current_state,
        )
        object.__setattr__(
            self,
            "previous_state",
            previous_state,
        )

        if self.event_version not in SUPPORTED_TRACKING_EVENT_VERSIONS:
            raise ValueError("Unsupported tracking event version")

        if EVENT_CURRENT_STATE[event_type] is not current_state:
            raise ValueError("event_type and current_state do not match")

        for field_name in (
            "event_id",
            "shipment_reference",
            "correlation_id",
            "idempotency_key",
            "source",
            "safe_summary",
        ):
            object.__setattr__(
                self,
                field_name,
                _require_non_empty(
                    str(getattr(self, field_name)),
                    field_name=field_name,
                ),
            )

        _require_timezone_aware(
            self.occurred_at,
            field_name="occurred_at",
        )

        if self.recorded_at is not None:
            _require_timezone_aware(
                self.recorded_at,
                field_name="recorded_at",
            )

            if self.recorded_at < self.occurred_at:
                raise ValueError("recorded_at must not be earlier than occurred_at")

        for field_name in (
            "tracking_reference",
            "provider_id",
            "provider_event_code",
            "causation_id",
        ):
            value = getattr(self, field_name)

            if value is not None:
                object.__setattr__(
                    self,
                    field_name,
                    _require_non_empty(
                        str(value),
                        field_name=field_name,
                    ),
                )

        object.__setattr__(
            self,
            "details",
            _normalize_safe_pairs(
                self.details,
                field_name="details",
            ),
        )

        normalized_warnings: list[str] = []

        for warning in self.warnings:
            normalized_warnings.append(
                _require_non_empty(
                    warning,
                    field_name="warning",
                )
            )

        object.__setattr__(
            self,
            "warnings",
            tuple(normalized_warnings),
        )

        if not self.preview_only:
            raise ValueError("Shipment events must remain preview-only")

        if self.live_write:
            raise ValueError("Live writes are disabled")

        if self.provider_call_performed:
            raise ValueError("Real provider calls are disabled")

        if self.telegram_api_call_performed:
            raise ValueError("Telegram API calls are disabled")

        if self.cross_repository_write:
            raise ValueError("Cross-repository writes are disabled")

    def to_mapping(self) -> dict[str, Any]:
        """Return a deterministic serialization-ready mapping."""

        return {
            "causation_id": self.causation_id,
            "correlation_id": self.correlation_id,
            "cross_repository_write": (self.cross_repository_write),
            "current_state": self.current_state.value,
            "details": dict(self.details),
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "event_version": self.event_version,
            "idempotency_key": self.idempotency_key,
            "live_write": self.live_write,
            "occurred_at": self.occurred_at.isoformat(),
            "preview_only": self.preview_only,
            "previous_state": (
                self.previous_state.value if self.previous_state is not None else None
            ),
            "provider_call_performed": (self.provider_call_performed),
            "provider_event_code": self.provider_event_code,
            "provider_id": self.provider_id,
            "recorded_at": (self.recorded_at.isoformat() if self.recorded_at is not None else None),
            "safe_summary": self.safe_summary,
            "shipment_reference": self.shipment_reference,
            "source": self.source,
            "telegram_api_call_performed": (self.telegram_api_call_performed),
            "tracking_reference": self.tracking_reference,
            "warnings": list(self.warnings),
        }

    def to_json(self) -> str:
        """Serialize deterministically for previews and fixtures."""

        return json.dumps(
            self.to_mapping(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
