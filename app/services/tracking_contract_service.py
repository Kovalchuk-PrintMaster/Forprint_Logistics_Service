from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.events import (
    LogisticsNotificationProjection,
)
from app.domain.shipments import ShipmentStatus
from app.domain.tracking import (
    EVENT_CURRENT_STATE,
    TERMINAL_SHIPMENT_STATES,
    TRACKING_EVENT_SCHEMA_VERSION,
    ProviderTrackingObservation,
    ShipmentEventEnvelope,
    ShipmentEventType,
    TrackingProcessingDecision,
    stable_contract_digest,
)

_ALLOWED_PREVIOUS_STATES: dict[
    ShipmentEventType,
    frozenset[ShipmentStatus | None],
] = {
    ShipmentEventType.SHIPMENT_CREATED: frozenset(
        {
            None,
            ShipmentStatus.DRAFT,
            ShipmentStatus.PREVIEW_READY,
        }
    ),
    ShipmentEventType.TRACKING_UPDATED: frozenset(
        {
            ShipmentStatus.DRAFT_CREATED,
            ShipmentStatus.PREVIEW_READY,
            ShipmentStatus.TRACKING_REQUESTED,
            ShipmentStatus.TRACKING,
            ShipmentStatus.TRACKING_UPDATED,
            ShipmentStatus.NEEDS_ATTENTION,
        }
    ),
    ShipmentEventType.ARRIVED: frozenset(
        {
            ShipmentStatus.TRACKING_REQUESTED,
            ShipmentStatus.TRACKING,
            ShipmentStatus.TRACKING_UPDATED,
            ShipmentStatus.NEEDS_ATTENTION,
        }
    ),
    ShipmentEventType.DELIVERED: frozenset(
        {
            ShipmentStatus.ARRIVED,
            ShipmentStatus.TRACKING_UPDATED,
            ShipmentStatus.NEEDS_ATTENTION,
        }
    ),
    ShipmentEventType.FAILED: frozenset(set(ShipmentStatus) - TERMINAL_SHIPMENT_STATES),
    ShipmentEventType.NEEDS_ATTENTION: frozenset(set(ShipmentStatus) - TERMINAL_SHIPMENT_STATES),
}


_PROVIDER_STATUS_EVENT_MAP: dict[
    str,
    ShipmentEventType,
] = {
    "arrived": ShipmentEventType.ARRIVED,
    "at_destination": ShipmentEventType.ARRIVED,
    "at_pickup_point": ShipmentEventType.ARRIVED,
    "created": ShipmentEventType.SHIPMENT_CREATED,
    "delivered": ShipmentEventType.DELIVERED,
    "delivery_completed": ShipmentEventType.DELIVERED,
    "failed": ShipmentEventType.FAILED,
    "failure": ShipmentEventType.FAILED,
    "in_transit": ShipmentEventType.TRACKING_UPDATED,
    "needs_attention": ShipmentEventType.NEEDS_ATTENTION,
    "shipment_created": ShipmentEventType.SHIPMENT_CREATED,
    "tracking": ShipmentEventType.TRACKING_UPDATED,
    "tracking_updated": ShipmentEventType.TRACKING_UPDATED,
}


_SAFE_SUMMARIES: dict[
    ShipmentEventType,
    str,
] = {
    ShipmentEventType.SHIPMENT_CREATED: ("Shipment entered the Logistics lifecycle."),
    ShipmentEventType.TRACKING_UPDATED: ("A normalized tracking update was accepted."),
    ShipmentEventType.ARRIVED: ("Shipment arrival was recorded."),
    ShipmentEventType.DELIVERED: ("Shipment delivery was confirmed."),
    ShipmentEventType.FAILED: ("Shipment workflow entered a failed state."),
    ShipmentEventType.NEEDS_ATTENTION: ("Shipment requires human attention."),
}


@dataclass(frozen=True, slots=True)
class TrackingContractResult:
    """Result of one deterministic observation-processing attempt."""

    decision: TrackingProcessingDecision
    reason_code: str
    event: ShipmentEventEnvelope | None = None
    notification: LogisticsNotificationProjection | None = None

    @property
    def accepted(self) -> bool:
        return self.decision is TrackingProcessingDecision.ACCEPTED

    @property
    def replay_safe(self) -> bool:
        return self.decision in {
            TrackingProcessingDecision.ACCEPTED,
            TrackingProcessingDecision.DUPLICATE,
            TrackingProcessingDecision.OUT_OF_ORDER,
            TrackingProcessingDecision.INVALID_TRANSITION,
            TrackingProcessingDecision.TERMINAL_STATE,
        }


class TrackingContractService:
    """Pure provider-neutral tracking event contract service.

    The service has no repository, database, provider, Telegram,
    queue, worker or cross-repository dependency.
    """

    @staticmethod
    def normalize_provider_status(
        provider_status: str,
    ) -> tuple[ShipmentEventType, tuple[str, ...]]:
        normalized = provider_status.strip().casefold().replace("-", "_").replace(" ", "_")

        if not normalized:
            raise ValueError("provider_status must not be empty")

        event_type = _PROVIDER_STATUS_EVENT_MAP.get(normalized)

        if event_type is not None:
            return event_type, ()

        return (
            ShipmentEventType.NEEDS_ATTENTION,
            ("Provider status was not recognized and requires human review.",),
        )

    @staticmethod
    def transition_allowed(
        previous_state: ShipmentStatus | None,
        event_type: ShipmentEventType,
    ) -> bool:
        return previous_state in _ALLOWED_PREVIOUS_STATES[event_type]

    @staticmethod
    def _latest_event(
        history: tuple[ShipmentEventEnvelope, ...],
        *,
        shipment_reference: str,
    ) -> ShipmentEventEnvelope | None:
        relevant = [event for event in history if event.shipment_reference == shipment_reference]

        if not relevant:
            return None

        return max(
            relevant,
            key=lambda event: (
                event.occurred_at,
                event.event_id,
            ),
        )

    @staticmethod
    def _identity(
        observation: ProviderTrackingObservation,
        event_type: ShipmentEventType,
    ) -> tuple[str, str]:
        digest = stable_contract_digest(
            TRACKING_EVENT_SCHEMA_VERSION,
            event_type.value,
            observation.logical_fingerprint,
        )

        return (
            f"event_{digest}",
            f"event_idem_{digest}",
        )

    def process_observation(
        self,
        observation: ProviderTrackingObservation,
        *,
        correlation_id: str,
        history: tuple[
            ShipmentEventEnvelope,
            ...,
        ] = (),
        recipient_reference: str | None = None,
        event_type: ShipmentEventType | None = None,
        causation_id: str | None = None,
        recorded_at: datetime | None = None,
    ) -> TrackingContractResult:
        correlation_id = correlation_id.strip()

        if not correlation_id:
            raise ValueError("correlation_id must not be empty")

        normalized_event_type: ShipmentEventType
        warnings: tuple[str, ...]

        if event_type is None:
            (
                normalized_event_type,
                warnings,
            ) = self.normalize_provider_status(observation.provider_status)
        else:
            normalized_event_type = ShipmentEventType(event_type)
            warnings = ()

        event_id, idempotency_key = self._identity(
            observation,
            normalized_event_type,
        )

        for existing in history:
            if (
                existing.shipment_reference == observation.shipment_reference
                and existing.idempotency_key == idempotency_key
            ):
                return TrackingContractResult(
                    decision=(TrackingProcessingDecision.DUPLICATE),
                    reason_code="logical_duplicate",
                    event=existing,
                    notification=None,
                )

        latest = self._latest_event(
            history,
            shipment_reference=(observation.shipment_reference),
        )

        if latest is not None:
            if observation.occurred_at <= latest.occurred_at:
                return TrackingContractResult(
                    decision=(TrackingProcessingDecision.OUT_OF_ORDER),
                    reason_code=("observation_not_newer_than_latest"),
                )

            if latest.current_state in TERMINAL_SHIPMENT_STATES:
                return TrackingContractResult(
                    decision=(TrackingProcessingDecision.TERMINAL_STATE),
                    reason_code=("terminal_state_rejects_new_event"),
                )

            previous_state: ShipmentStatus | None = latest.current_state
        else:
            previous_state = None

        if not self.transition_allowed(
            previous_state,
            normalized_event_type,
        ):
            return TrackingContractResult(
                decision=(TrackingProcessingDecision.INVALID_TRANSITION),
                reason_code="transition_not_allowed",
            )

        details = (
            (
                "provider_status",
                observation.provider_status,
            ),
            *observation.safe_metadata,
        )

        event = ShipmentEventEnvelope(
            event_id=event_id,
            event_type=normalized_event_type,
            event_version=TRACKING_EVENT_SCHEMA_VERSION,
            occurred_at=observation.occurred_at,
            recorded_at=recorded_at,
            shipment_reference=(observation.shipment_reference),
            tracking_reference=(observation.tracking_reference),
            provider_id=observation.provider_id,
            provider_event_code=(observation.provider_event_code),
            previous_state=previous_state,
            current_state=EVENT_CURRENT_STATE[normalized_event_type],
            correlation_id=correlation_id,
            causation_id=(causation_id or (latest.event_id if latest is not None else None)),
            idempotency_key=idempotency_key,
            source="logistics_service",
            details=details,
            safe_summary=_SAFE_SUMMARIES[normalized_event_type],
            warnings=warnings,
            preview_only=True,
            live_write=False,
            provider_call_performed=False,
            telegram_api_call_performed=False,
            cross_repository_write=False,
        )

        notification = LogisticsNotificationProjection.from_event(
            event,
            recipient_reference=recipient_reference,
        )

        return TrackingContractResult(
            decision=TrackingProcessingDecision.ACCEPTED,
            reason_code="event_accepted",
            event=event,
            notification=notification,
        )
