from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from app.domain import (
    AddressBookEntry,
    AddressSnapshot,
    LogisticsProvider,
    ProviderCapability,
    RecipientRef,
    ShipmentDraft,
)
from app.services import (
    AddressBookService,
    ShipmentDraftService,
)
from app.storage import (
    InMemoryLogisticsRepository,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_FIXTURE_PATH = PROJECT_ROOT / "examples/fixtures/address_book/test_address_book.yaml"
DEFAULT_WORKFLOW_PATH = PROJECT_ROOT / "examples/workflows/address_book_lookup_preview.yaml"

REQUIRED_SAFETY_FLAGS = {
    "non_canonical": True,
    "preview_only": True,
    "live_provider_write": False,
    "synthetic_data": True,
    "real_customer_data": False,
}


@dataclass(frozen=True, slots=True)
class TestAddressBookPreview:
    entries: tuple[AddressBookEntry, ...]
    selected_entry: AddressBookEntry
    snapshot: AddressSnapshot
    provider: LogisticsProvider
    draft: ShipmentDraft
    lookup_alias: str
    provider_call_performed: bool
    repository: InMemoryLogisticsRepository


def load_yaml_mapping(
    path: Path,
) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")

    return data


def require_mapping(
    value: object,
    name: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a mapping")

    return value


def require_list(
    value: object,
    name: str,
) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")

    return value


def optional_string(
    value: object,
) -> str | None:
    if value is None:
        return None

    return str(value)


def string_tuple(
    value: object,
    name: str,
) -> tuple[str, ...]:
    items = require_list(value, name)
    return tuple(str(item) for item in items)


def string_pairs(
    value: object,
) -> tuple[tuple[str, str], ...]:
    if value is None:
        return ()

    mapping = require_mapping(
        value,
        "metadata",
    )

    return tuple((str(key), str(item)) for key, item in mapping.items())


def validate_safety_flags(
    name: str,
    data: dict[str, Any],
) -> None:
    for key, expected in REQUIRED_SAFETY_FLAGS.items():
        if data.get(key) is not expected:
            raise ValueError(f"{name}: {key} must be {str(expected).lower()}")


def build_address_book_entry(
    raw_entry: object,
) -> AddressBookEntry:
    entry = require_mapping(
        raw_entry,
        "address book entry",
    )
    recipient_data = require_mapping(
        entry.get("recipient"),
        "recipient",
    )
    address_data = require_mapping(
        entry.get("address"),
        "address",
    )

    if entry.get("synthetic_data") is not True:
        raise ValueError("Address book entry must be synthetic")

    if entry.get("real_customer_data") is not False:
        raise ValueError("Real customer data is forbidden")

    recipient = RecipientRef(
        recipient_ref=str(recipient_data["recipient_ref"]),
        display_name=str(recipient_data["display_name"]),
        phone=optional_string(recipient_data.get("phone")),
        source_system=str(
            recipient_data.get(
                "source_system",
                "local_fixture",
            )
        ),
        non_canonical=bool(recipient_data["non_canonical"]),
    )

    return AddressBookEntry(
        entry_id=str(entry["entry_id"]),
        recipient=recipient,
        aliases=string_tuple(
            entry.get("aliases"),
            "aliases",
        ),
        country_code=str(address_data["country_code"]),
        city=str(address_data["city"]),
        address_line_1=str(address_data["address_line_1"]),
        postal_code=optional_string(address_data.get("postal_code")),
        address_line_2=optional_string(address_data.get("address_line_2")),
        provider_location_ref=optional_string(address_data.get("provider_location_ref")),
        area_hint=optional_string(entry.get("area_hint")),
        search_tokens=string_tuple(
            entry.get("search_tokens", []),
            "search_tokens",
        ),
        source_system=str(
            entry.get(
                "source_system",
                "local_fixture",
            )
        ),
        non_canonical=bool(entry["non_canonical"]),
        logistics_reference_only=bool(entry["logistics_reference_only"]),
    )


def build_test_address_book_preview(
    fixture_path: Path = (DEFAULT_FIXTURE_PATH),
    workflow_path: Path = (DEFAULT_WORKFLOW_PATH),
) -> TestAddressBookPreview:
    fixture = load_yaml_mapping(fixture_path)
    workflow = load_yaml_mapping(workflow_path)

    validate_safety_flags(
        fixture_path.name,
        fixture,
    )
    validate_safety_flags(
        workflow_path.name,
        workflow,
    )

    raw_entries = require_list(
        fixture.get("entries"),
        "entries",
    )
    entries = tuple(build_address_book_entry(raw) for raw in raw_entries)

    repository = InMemoryLogisticsRepository()
    address_book_service = AddressBookService(repository)
    shipment_service = ShipmentDraftService(repository)

    for entry in entries:
        address_book_service.save_entry(entry)

    lookup_data = require_mapping(
        workflow.get("lookup"),
        "lookup",
    )
    alias = str(lookup_data["alias"])
    raw_hint = lookup_data.get("city_or_area_hint")
    hint = None if raw_hint is None else str(raw_hint)

    matches = address_book_service.lookup(
        alias,
        city_or_area_hint=hint,
    )

    if len(matches) != 1:
        raise ValueError("Lookup must resolve exactly one synthetic address book entry")

    selected_entry = matches[0]
    expected_entry_id = str(lookup_data["expected_entry_id"])

    if selected_entry.entry_id != expected_entry_id:
        raise ValueError("Lookup result does not match expected_entry_id")

    snapshot = address_book_service.create_address_snapshot(selected_entry.entry_id)

    provider_data = require_mapping(
        workflow.get("provider"),
        "provider",
    )
    capabilities = string_tuple(
        provider_data.get(
            "capabilities",
            [],
        ),
        "provider capabilities",
    )

    provider = LogisticsProvider(
        provider_id=str(provider_data["provider_id"]),
        display_name=str(provider_data["display_name"]),
        capabilities=frozenset(ProviderCapability(item) for item in capabilities),
        live_write_enabled=bool(
            provider_data.get(
                "live_write_enabled",
                False,
            )
        ),
    )

    draft_data = require_mapping(
        workflow.get("shipment_draft"),
        "shipment_draft",
    )

    draft = shipment_service.create_preview(
        shipment_id=str(draft_data["shipment_id"]),
        external_order_ref=str(draft_data["external_order_ref"]),
        provider=provider,
        recipient=(selected_entry.recipient),
        destination=snapshot,
        package_description=str(draft_data["package_description"]),
        weight_kg=float(draft_data["weight_kg"]),
        metadata=string_pairs(draft_data.get("metadata")),
    )

    expected = require_mapping(
        workflow.get("expected"),
        "expected",
    )

    if len(entries) != int(expected["entry_count"]):
        raise ValueError("Unexpected address book entry count")

    provider_call_performed = bool(expected["provider_call_performed"])

    if provider_call_performed:
        raise ValueError("Provider calls must remain disabled")

    if (
        not selected_entry.non_canonical
        or not snapshot.shipment_time_snapshot
        or not draft.preview_only
        or draft.live_provider_write
    ):
        raise ValueError("Unsafe address book preview state")

    return TestAddressBookPreview(
        entries=entries,
        selected_entry=selected_entry,
        snapshot=snapshot,
        provider=provider,
        draft=draft,
        lookup_alias=alias,
        provider_call_performed=(provider_call_performed),
        repository=repository,
    )


def render_preview(
    preview: TestAddressBookPreview,
) -> str:
    lines = [
        ("ForPrint Logistics Service — test address book preview"),
        "",
        ("Test address book: local synthetic entries"),
        (f"Entry count: {len(preview.entries)}"),
        (f"Lookup by alias: OK ({preview.lookup_alias} -> {preview.selected_entry.entry_id})"),
        ("Recipient reference: non-canonical"),
        ("Address snapshot: shipment-time snapshot"),
        ("Shipment draft preview: created without provider API call"),
        "Live provider write: disabled",
        "",
        ("No external provider call was performed."),
    ]

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=("Show the safe local synthetic test address book preview.")
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=DEFAULT_FIXTURE_PATH,
    )
    parser.add_argument(
        "--workflow",
        type=Path,
        default=DEFAULT_WORKFLOW_PATH,
    )
    args = parser.parse_args()

    try:
        preview = build_test_address_book_preview(
            args.fixture,
            args.workflow,
        )
    except (
        FileNotFoundError,
        OSError,
        ValueError,
        yaml.YAMLError,
    ) as exc:
        print(f"Test address book preview failed: {exc}")
        return 1

    print(render_preview(preview))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
