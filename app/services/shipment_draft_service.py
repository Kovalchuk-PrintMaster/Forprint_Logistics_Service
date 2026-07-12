from __future__ import annotations

from app.domain import (
    AddressSnapshot,
    LogisticsProvider,
    RecipientRef,
    ShipmentDraft,
    ShipmentStatus,
)
from app.services.errors import LocalModelSafetyError
from app.storage import LogisticsRepository


class ShipmentDraftService:
    """Create and persist preview-only shipment drafts."""

    def __init__(
        self,
        repository: LogisticsRepository,
    ) -> None:
        self._repository = repository

    def create_preview(
        self,
        *,
        shipment_id: str,
        external_order_ref: str,
        provider: LogisticsProvider,
        recipient: RecipientRef,
        destination: AddressSnapshot,
        package_description: str,
        weight_kg: float,
        metadata: tuple[
            tuple[str, str],
            ...,
        ] = (),
    ) -> ShipmentDraft:
        if not recipient.non_canonical:
            raise LocalModelSafetyError("Recipient must remain non-canonical")

        if not destination.shipment_time_snapshot:
            raise LocalModelSafetyError("Destination must remain a shipment-time snapshot")

        self._repository.save_provider(provider)
        self._repository.save_recipient(recipient)

        draft = ShipmentDraft(
            shipment_id=shipment_id,
            external_order_ref=external_order_ref,
            provider_id=provider.provider_id,
            recipient=recipient,
            destination=destination,
            package_description=package_description,
            weight_kg=weight_kg,
            status=ShipmentStatus.PREVIEW_READY,
            metadata=metadata,
            preview_only=True,
            live_provider_write=False,
        )

        if not draft.preview_only or draft.live_provider_write:
            raise LocalModelSafetyError("Unsafe shipment draft state")

        return self._repository.save_shipment_draft(draft)
