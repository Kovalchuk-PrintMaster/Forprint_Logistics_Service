from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from app.adapters.providers import (
    LiveProviderWriteDisabledError,
    build_synthetic_provider_registry,
)
from app.domain import (
    AddressSnapshot,
    AddressValidationRequest,
    DeliveryQuoteLookupRequest,
    DryRunExecutionMetadata,
    ProviderOperation,
    RecipientRef,
    RecipientValidationRequest,
    ShipmentDraft,
    ShipmentPayloadPreviewRequest,
    TrackingLookupRequest,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _error_data(error: object) -> dict[str, object]:
    return {
        "code": error.code.value,
        "safe_message": error.safe_message,
        "retryable": error.retryable,
    }


def build_preview_data() -> dict[str, Any]:
    """Build a deterministic provider contract preview."""

    registry = build_synthetic_provider_registry(enabled=True)

    provider_descriptions = registry.list_descriptions(include_disabled=True)

    parcel = registry.resolve("synthetic_parcel")
    courier = registry.resolve("synthetic_taxi_courier")

    recipient = RecipientRef(
        recipient_ref="synthetic_recipient_001",
        display_name="Synthetic Recipient",
        phone="+380000000001",
        source_system="synthetic_contract_fixture",
    )
    address = AddressSnapshot(
        country_code="UA",
        city="Synthetic City",
        address_line_1="Synthetic Street 1",
        postal_code="00001",
        provider_location_ref=("synthetic_location_001"),
    )
    draft = ShipmentDraft(
        shipment_id="synthetic_shipment_001",
        external_order_ref=("synthetic_order_ref_001"),
        provider_id=parcel.provider.provider_id,
        recipient=recipient,
        destination=address,
        package_description=("Synthetic provider contract package"),
        weight_kg=1.25,
    )

    recipient_result = parcel.validate_recipient(
        RecipientValidationRequest(
            correlation_ref=("recipient_validation_001"),
            recipient=recipient,
            address=address,
        )
    )
    address_result = parcel.validate_address(
        AddressValidationRequest(
            correlation_ref=("address_validation_001"),
            address=address,
        )
    )
    preview_result = parcel.build_shipment_payload_preview(
        ShipmentPayloadPreviewRequest(
            correlation_ref=("shipment_preview_001"),
            draft=draft,
        )
    )
    tracking_result = courier.track(
        TrackingLookupRequest(
            provider_id=(courier.provider.provider_id),
            tracking_number=("SYNTHETIC-TRACK-001"),
            correlation_ref=("tracking_lookup_001"),
        )
    )
    quote_result = parcel.lookup_delivery_quote(
        DeliveryQuoteLookupRequest(
            provider_id=parcel.provider.provider_id,
            execution=DryRunExecutionMetadata(
                operation=(ProviderOperation.DELIVERY_QUOTE_LOOKUP),
                correlation_ref=("quote_lookup_001"),
            ),
            normalized_input_summary=(
                ("weight_kg", "1.25"),
                (
                    "destination_city",
                    address.city,
                ),
            ),
        )
    )

    try:
        parcel.create_shipment(draft)
    except LiveProviderWriteDisabledError as exc:
        live_write_error = exc.provider_error
    else:
        raise AssertionError("Synthetic adapter unexpectedly allowed live shipment creation")

    envelope = preview_result.envelope

    return {
        "schema_version": ("provider_adapter_contract_preview_v0_1"),
        "preview_only": True,
        "live_write": False,
        "provider_call_performed": False,
        "providers": [
            {
                "provider_id": item.provider_id,
                "display_name": item.display_name,
                "enabled": item.enabled,
                "live_write_enabled": (item.live_write_enabled),
                "capabilities": [
                    support.capability.value
                    for support in (item.capability_description.capabilities)
                    if support.supported
                ],
            }
            for item in provider_descriptions
        ],
        "recipient_validation": {
            "valid": recipient_result.valid,
            "errors": [_error_data(error) for error in recipient_result.errors],
        },
        "address_validation": {
            "valid": address_result.valid,
            "errors": [_error_data(error) for error in address_result.errors],
        },
        "shipment_preview": {
            "provider_id": envelope.provider_id,
            "operation": envelope.operation.value,
            "correlation_ref": (envelope.correlation_ref),
            "preview_only": envelope.preview_only,
            "live_write": envelope.live_write,
            "provider_call_performed": (envelope.execution.provider_call_performed),
            "provider_payload_preview": (envelope.payload_mapping()),
            "warnings": list(envelope.warnings),
            "errors": [_error_data(error) for error in preview_result.errors],
        },
        "unsupported_tracking": {
            "provider_id": (tracking_result.provider_id),
            "read_only": tracking_result.read_only,
            "provider_call_performed": (tracking_result.provider_call_performed),
            "errors": [_error_data(error) for error in tracking_result.errors],
        },
        "unsupported_quote": {
            "available": quote_result.available,
            "provider_call_performed": (quote_result.execution.provider_call_performed),
            "errors": [_error_data(error) for error in quote_result.errors],
        },
        "live_write_disabled": {
            "code": live_write_error.code.value,
            "retryable": (live_write_error.retryable),
            "safe_message": (live_write_error.safe_message),
        },
    }


def write_preview_artifact(
    data: dict[str, Any],
    project_root: Path = PROJECT_ROOT,
) -> Path:
    output_path = project_root / "reports" / "previews" / "provider_adapter_contract_preview.json"
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output_path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return output_path


def _cell(value: object, width: int) -> str:
    text = str(value)

    if len(text) > width:
        text = text[: max(0, width - 1)] + "…"

    return f" {text.ljust(width)} "


def _table(
    headers: Sequence[str],
    rows: Sequence[Sequence[object]],
    widths: Sequence[int],
) -> str:
    def border(
        left: str,
        middle: str,
        right: str,
    ) -> str:
        return left + middle.join("─" * (width + 2) for width in widths) + right

    lines = [
        border("┌", "┬", "┐"),
        "│" + "│".join(_cell(value, widths[index]) for index, value in enumerate(headers)) + "│",
        border("├", "┼", "┤"),
    ]

    for row in rows:
        lines.append(
            "│" + "│".join(_cell(value, widths[index]) for index, value in enumerate(row)) + "│"
        )

    lines.append(border("└", "┴", "┘"))

    return "\n".join(lines)


def build_console_summary(
    data: dict[str, Any],
) -> str:
    provider_rows = []

    for item in data["providers"]:
        marker = ">" if item["provider_id"] == "synthetic_parcel" else ""
        provider_rows.append(
            (
                marker,
                item["provider_id"],
                "enabled" if item["enabled"] else "disabled",
                len(item["capabilities"]),
                "NO",
            )
        )

    signal_rows = (
        (
            "Recipient validation",
            ("OK" if data["recipient_validation"]["valid"] else "FAILED"),
            "synthetic typed result",
        ),
        (
            "Address validation",
            ("OK" if data["address_validation"]["valid"] else "FAILED"),
            "synthetic typed result",
        ),
        (
            "Shipment preview",
            "OK",
            "preview-only envelope",
        ),
        (
            "Courier tracking",
            "UNSUPPORTED",
            "explicit typed error",
        ),
        (
            "Delivery quote",
            "UNSUPPORTED",
            "explicit typed error",
        ),
        (
            "Live shipment write",
            "DISABLED",
            "final safety gate",
        ),
    )

    return "\n".join(
        [
            ("ForPrint Logistics Service — provider adapter contract preview"),
            "",
            _table(
                (
                    "",
                    "Provider",
                    "State",
                    "Caps",
                    "Live",
                ),
                provider_rows,
                (1, 27, 8, 4, 4),
            ),
            "",
            _table(
                (
                    "Contract signal",
                    "Status",
                    "Evidence",
                ),
                signal_rows,
                (22, 11, 24),
            ),
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=("Preview synthetic provider adapter contracts without provider calls.")
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
    )
    args = parser.parse_args()

    data = build_preview_data()
    path = write_preview_artifact(
        data,
        args.project_root.resolve(),
    )

    print(build_console_summary(data))
    print("")
    print(f"Preview artifact: {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
