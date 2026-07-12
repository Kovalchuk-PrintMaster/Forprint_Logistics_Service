from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from app.domain import (
    AddressSnapshot,
    LogisticsNotificationEvent,
    LogisticsNotificationType,
    LogisticsProvider,
    ProviderCapability,
    RecipientRef,
    ShipmentDraft,
    ShipmentStatus,
    TrackingEvent,
    TrackingRequest,
)
from app.services import (
    NotificationEventService,
    ShipmentDraftService,
    TrackingEventService,
)
from app.storage import InMemoryLogisticsRepository

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EXAMPLES_ROOT = PROJECT_ROOT / "examples/workflows"

EXAMPLE_FILENAMES = (
    "shipment_draft_preview.yaml",
    "tracking_request_preview.yaml",
    "notification_event_preview.yaml",
)


@dataclass(frozen=True, slots=True)
class LocalModelPreview:
    provider: LogisticsProvider
    recipient: RecipientRef
    draft: ShipmentDraft
    tracking_request: TrackingRequest
    tracking_events: tuple[TrackingEvent, ...]
    notification: LogisticsNotificationEvent
    intended_surfaces: tuple[str, ...]
    repository: InMemoryLogisticsRepository


def load_yaml_mapping(
    path: Path,
) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")

    return data


def load_workflow_examples(
    examples_root: Path,
) -> dict[str, dict[str, Any]]:
    examples: dict[str, dict[str, Any]] = {}

    for filename in EXAMPLE_FILENAMES:
        path = examples_root / filename

        if not path.is_file():
            raise FileNotFoundError(path)

        examples[filename] = load_yaml_mapping(path)

    return examples


def validate_safety_flags(
    filename: str,
    data: dict[str, Any],
) -> None:
    if data.get("non_canonical") is not True:
        raise ValueError(f"{filename}: non_canonical must be true")

    if data.get("preview_only") is not True:
        raise ValueError(f"{filename}: preview_only must be true")

    if data.get("live_provider_write") is not False:
        raise ValueError(f"{filename}: live_provider_write must be false")


def parse_datetime(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Datetime value must be a string")

    parsed = datetime.fromisoformat(value)

    if parsed.tzinfo is None:
        raise ValueError("Datetime value must include timezone")

    return parsed


def string_pairs(
    value: object,
) -> tuple[tuple[str, str], ...]:
    if value is None:
        return ()

    if not isinstance(value, dict):
        raise ValueError("Expected a mapping of string values")

    return tuple((str(key), str(item)) for key, item in value.items())


def build_local_model_preview(
    examples_root: Path = DEFAULT_EXAMPLES_ROOT,
) -> LocalModelPreview:
    examples = load_workflow_examples(examples_root)

    for filename, data in examples.items():
        validate_safety_flags(
            filename,
            data,
        )

    shipment_data = examples["shipment_draft_preview.yaml"]
    tracking_data = examples["tracking_request_preview.yaml"]
    notification_data = examples["notification_event_preview.yaml"]

    provider_data = shipment_data["provider"]
    recipient_data = shipment_data["recipient"]
    destination_data = shipment_data["destination"]
    draft_data = shipment_data["shipment_draft"]

    if not isinstance(provider_data, dict):
        raise ValueError("provider must be a mapping")

    if not isinstance(recipient_data, dict):
        raise ValueError("recipient must be a mapping")

    if not isinstance(destination_data, dict):
        raise ValueError("destination must be a mapping")

    if not isinstance(draft_data, dict):
        raise ValueError("shipment_draft must be a mapping")

    provider = LogisticsProvider(
        provider_id=str(provider_data["provider_id"]),
        display_name=str(provider_data["display_name"]),
        capabilities=frozenset(
            ProviderCapability(str(capability)) for capability in provider_data["capabilities"]
        ),
    )

    recipient = RecipientRef(
        recipient_ref=str(recipient_data["recipient_ref"]),
        display_name=str(recipient_data["display_name"]),
        phone=str(recipient_data["phone"]),
        source_system=str(recipient_data["source_system"]),
        non_canonical=bool(recipient_data["non_canonical"]),
    )

    destination = AddressSnapshot(
        country_code=str(destination_data["country_code"]),
        city=str(destination_data["city"]),
        address_line_1=str(destination_data["address_line_1"]),
        postal_code=str(destination_data["postal_code"]),
        provider_location_ref=str(destination_data["provider_location_ref"]),
        shipment_time_snapshot=bool(destination_data["shipment_time_snapshot"]),
    )

    repository = InMemoryLogisticsRepository()

    shipment_service = ShipmentDraftService(repository)
    tracking_service = TrackingEventService(repository)
    notification_service = NotificationEventService(repository)

    draft = shipment_service.create_preview(
        shipment_id=str(draft_data["shipment_id"]),
        external_order_ref=str(draft_data["external_order_ref"]),
        provider=provider,
        recipient=recipient,
        destination=destination,
        package_description=str(draft_data["package_description"]),
        weight_kg=float(draft_data["weight_kg"]),
        metadata=string_pairs(draft_data.get("metadata")),
    )

    expected_status = ShipmentStatus(str(draft_data["status"]))

    if draft.status is not expected_status:
        raise ValueError("Created shipment draft status does not match the workflow example")

    request_data = tracking_data["tracking_request"]

    if not isinstance(request_data, dict):
        raise ValueError("tracking_request must be a mapping")

    if request_data.get("local_only") is not True:
        raise ValueError("Tracking request must be local-only")

    if request_data.get("provider_call_performed") is not False:
        raise ValueError("Provider call must not be performed")

    if str(request_data["provider_id"]) != provider.provider_id:
        raise ValueError("Tracking provider does not match shipment provider")

    tracking_request = tracking_service.create_local_request(
        provider_id=str(request_data["provider_id"]),
        tracking_number=str(request_data["tracking_number"]),
        requested_at=parse_datetime(request_data["requested_at"]),
    )

    raw_tracking_events = tracking_data["tracking_events"]

    if not isinstance(
        raw_tracking_events,
        list,
    ):
        raise ValueError("tracking_events must be a list")

    tracking_events: list[TrackingEvent] = []

    for raw_event in raw_tracking_events:
        if not isinstance(raw_event, dict):
            raise ValueError("Each tracking event must be a mapping")

        if raw_event.get("local_record") is not True:
            raise ValueError("Tracking events must be local records")

        if str(raw_event["tracking_number"]) != tracking_request.tracking_number:
            raise ValueError("Tracking event number does not match the tracking request")

        tracking_events.append(
            tracking_service.record_local_event(
                event_id=str(raw_event["event_id"]),
                provider_id=str(raw_event["provider_id"]),
                tracking_number=str(raw_event["tracking_number"]),
                occurred_at=parse_datetime(raw_event["occurred_at"]),
                normalized_status=ShipmentStatus(str(raw_event["normalized_status"])),
                provider_status=str(raw_event["provider_status"]),
                description=str(raw_event["description"]),
            )
        )

    raw_notification = notification_data["notification_event"]

    if not isinstance(
        raw_notification,
        dict,
    ):
        raise ValueError("notification_event must be a mapping")

    if raw_notification.get("local_payload") is not True:
        raise ValueError("Notification must be a local payload")

    if raw_notification.get("delivery_performed") is not False:
        raise ValueError("Notification delivery must remain disabled")

    if str(raw_notification["shipment_id"]) != draft.shipment_id:
        raise ValueError("Notification shipment does not match shipment draft")

    notification = notification_service.create_local_payload(
        event_id=str(raw_notification["event_id"]),
        shipment_id=str(raw_notification["shipment_id"]),
        event_type=LogisticsNotificationType(str(raw_notification["event_type"])),
        occurred_at=parse_datetime(raw_notification["occurred_at"]),
        message=str(raw_notification["message"]),
        attributes=string_pairs(raw_notification.get("attributes")),
    )

    raw_surfaces = notification_data.get(
        "intended_display_surfaces",
        [],
    )

    if not isinstance(raw_surfaces, list):
        raise ValueError("intended_display_surfaces must be a list")

    intended_surfaces = tuple(str(surface) for surface in raw_surfaces)

    return LocalModelPreview(
        provider=provider,
        recipient=recipient,
        draft=draft,
        tracking_request=tracking_request,
        tracking_events=tuple(tracking_events),
        notification=notification,
        intended_surfaces=intended_surfaces,
        repository=repository,
    )


def render_preview(
    preview: LocalModelPreview,
) -> str:
    tracking_flow = " -> ".join(event.normalized_status.value for event in preview.tracking_events)

    surface_names = {
        "telegram_bot": "Telegram Bot",
        "crm": "CRM",
        "website": "Website",
    }

    display_surfaces = " / ".join(
        surface_names.get(surface, surface) for surface in preview.intended_surfaces
    )

    rows = (
        (
            "Provider",
            (f"{preview.provider.display_name} [{preview.provider.provider_id}]"),
        ),
        (
            "Recipient",
            (f"{preview.recipient.display_name} [{preview.recipient.recipient_ref}]"),
        ),
        (
            "Recipient ownership",
            "non-canonical",
        ),
        (
            "Address ownership",
            "shipment-time snapshot",
        ),
        (
            "Shipment draft",
            (f"{preview.draft.shipment_id} / {preview.draft.status.value}"),
        ),
        (
            "Shipment mode",
            "preview-only",
        ),
        (
            "Tracking request",
            (f"{preview.tracking_request.tracking_number} / local-only"),
        ),
        (
            "Tracking flow",
            tracking_flow,
        ),
        (
            "Notification",
            (f"{preview.notification.event_type.value} / local display payload"),
        ),
        (
            "Display surfaces",
            display_surfaces,
        ),
        (
            "Live provider write",
            "DISABLED",
        ),
    )

    label_width = max(len(label) for label, _value in rows)
    value_width = max(len(value) for _label, value in rows)

    top = "┌" + "─" * (label_width + 2) + "┬" + "─" * (value_width + 2) + "┐"
    middle = "├" + "─" * (label_width + 2) + "┼" + "─" * (value_width + 2) + "┤"
    bottom = "└" + "─" * (label_width + 2) + "┴" + "─" * (value_width + 2) + "┘"

    lines = [
        ("ForPrint Logistics Service — local model preview"),
        "",
        top,
        (f"│ {'Item'.ljust(label_width)} │ {'Value'.ljust(value_width)} │"),
        middle,
    ]

    for label, value in rows:
        lines.append(f"│ {label.ljust(label_width)} │ {value.ljust(value_width)} │")

    lines.extend(
        [
            bottom,
            "",
            (
                "Local repository records: "
                f"{len(preview.repository.list_providers())} "
                "provider, "
                f"{len(preview.repository.list_recipients())} "
                "recipient, "
                f"{len(preview.repository.list_shipment_drafts())} "
                "shipment draft, "
                f"{len(preview.repository.list_tracking_requests())} "
                "tracking request, "
                f"{len(preview.repository.list_tracking_events())} "
                "tracking events, "
                f"{len(preview.repository.list_notification_events())} "
                "notification"
            ),
            "",
            "No external provider call was performed.",
        ]
    )

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=("Show the safe local Logistics Service model preview.")
    )
    parser.add_argument(
        "--examples-root",
        type=Path,
        default=DEFAULT_EXAMPLES_ROOT,
    )
    args = parser.parse_args()

    try:
        preview = build_local_model_preview(args.examples_root)
    except (
        FileNotFoundError,
        OSError,
        ValueError,
        yaml.YAMLError,
    ) as exc:
        print(f"Local logistics model preview failed: {exc}")
        return 1

    print(render_preview(preview))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
