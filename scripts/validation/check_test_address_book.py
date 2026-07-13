from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from scripts.previews.preview_test_address_book import (
    DEFAULT_FIXTURE_PATH,
    DEFAULT_WORKFLOW_PATH,
    build_test_address_book_preview,
    load_yaml_mapping,
    validate_safety_flags,
)

SENSITIVE_KEY_NAMES = {
    "access_token",
    "api_key",
    "api_token",
    "credential",
    "credentials",
    "password",
    "secret",
    "token",
}

FORBIDDEN_OWNERSHIP_KEYS = {
    "canonical_client_id",
    "canonical_order_id",
    "client_account_id",
    "payment_id",
    "payment_status",
    "stock_reservation_id",
    "warehouse_stock_id",
    "one_c_id",
}


def find_forbidden_keys(
    value: object,
    *,
    location: str,
) -> tuple[str, ...]:
    findings: list[str] = []

    if isinstance(value, dict):
        for raw_key, child in value.items():
            key = str(raw_key)
            normalized = key.strip().lower()
            child_location = f"{location}.{key}"

            if normalized in SENSITIVE_KEY_NAMES:
                findings.append(f"Sensitive key found: {child_location}")

            if normalized in FORBIDDEN_OWNERSHIP_KEYS:
                findings.append(f"Forbidden ownership key found: {child_location}")

            findings.extend(
                find_forbidden_keys(
                    child,
                    location=(child_location),
                )
            )

    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(
                find_forbidden_keys(
                    child,
                    location=(f"{location}[{index}]"),
                )
            )

    return tuple(findings)


def validate_fixture(
    fixture: dict[str, Any],
) -> tuple[str, ...]:
    findings: list[str] = []

    entries = fixture.get("entries")

    if not isinstance(entries, list) or len(entries) < 3:
        return ("Fixture must contain at least three address book entries",)

    entry_ids: set[str] = set()
    entry_kinds: set[str] = set()

    for index, raw_entry in enumerate(entries):
        location = f"entries[{index}]"

        if not isinstance(
            raw_entry,
            dict,
        ):
            findings.append(f"{location} must be a mapping")
            continue

        entry_id = str(
            raw_entry.get(
                "entry_id",
                "",
            )
        )
        entry_kind = str(
            raw_entry.get(
                "entry_kind",
                "",
            )
        )

        if not entry_id.startswith("test_address_"):
            findings.append(f"{location}.entry_id must use a test_address_ prefix")

        if entry_id in entry_ids:
            findings.append(f"Duplicate entry_id: {entry_id}")

        entry_ids.add(entry_id)
        entry_kinds.add(entry_kind)

        for key, expected in (
            ("synthetic_data", True),
            ("real_customer_data", False),
            ("non_canonical", True),
            (
                "logistics_reference_only",
                True,
            ),
        ):
            if raw_entry.get(key) is not expected:
                findings.append(f"{location}.{key} must be {str(expected).lower()}")

        aliases = raw_entry.get("aliases")

        if not isinstance(aliases, list) or not aliases:
            findings.append(f"{location}.aliases must contain values")

        recipient = raw_entry.get("recipient")

        if not isinstance(
            recipient,
            dict,
        ):
            findings.append(f"{location}.recipient must be a mapping")
        else:
            recipient_ref = str(
                recipient.get(
                    "recipient_ref",
                    "",
                )
            )
            display_name = str(
                recipient.get(
                    "display_name",
                    "",
                )
            )

            if not recipient_ref.startswith("test_recipient_"):
                findings.append(f"{location}.recipient_ref must use a test prefix")

            if not display_name.startswith("Synthetic "):
                findings.append(f"{location}.display_name must be explicitly synthetic")

            if recipient.get("non_canonical") is not True:
                findings.append(f"{location}.recipient must remain non-canonical")

            if recipient.get("phone") is not None:
                findings.append(f"{location}.phone must be null in committed examples")

        address = raw_entry.get("address")

        if not isinstance(address, dict):
            findings.append(f"{location}.address must be a mapping")
        else:
            address_line = str(
                address.get(
                    "address_line_1",
                    "",
                )
            )

            if not address_line.startswith("Synthetic "):
                findings.append(f"{location}.address must be explicitly synthetic")

    required_kinds = {
        "kyiv_local",
        "warehouse",
        "office",
    }

    if not required_kinds.issubset(entry_kinds):
        findings.append("Fixture must contain Kyiv/local, warehouse and office entries")

    return tuple(findings)


def validate_workflow(
    workflow: dict[str, Any],
) -> tuple[str, ...]:
    findings: list[str] = []

    expected = workflow.get("expected")

    if not isinstance(expected, dict):
        return ("Workflow expected section must be a mapping",)

    required_expected = {
        "entry_count": 3,
        "lookup_by_alias": True,
        "recipient_non_canonical": True,
        "shipment_time_snapshot": True,
        "shipment_preview_created": True,
        "provider_call_performed": False,
        "live_provider_write": False,
    }

    for key, value in required_expected.items():
        if expected.get(key) != value:
            findings.append(f"expected.{key} must be {value!r}")

    provider = workflow.get("provider")

    if not isinstance(provider, dict):
        findings.append("provider must be a mapping")
    elif provider.get("live_write_enabled") is not False:
        findings.append("provider live writes must remain disabled")

    return tuple(findings)


def run_validation(
    fixture_path: Path = (DEFAULT_FIXTURE_PATH),
    workflow_path: Path = (DEFAULT_WORKFLOW_PATH),
) -> tuple[str, ...]:
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

    findings: list[str] = []
    findings.extend(validate_fixture(fixture))
    findings.extend(validate_workflow(workflow))
    findings.extend(
        find_forbidden_keys(
            fixture,
            location=fixture_path.name,
        )
    )
    findings.extend(
        find_forbidden_keys(
            workflow,
            location=workflow_path.name,
        )
    )

    if findings:
        return tuple(findings)

    preview = build_test_address_book_preview(
        fixture_path,
        workflow_path,
    )

    if (
        len(preview.entries) != 3
        or not (preview.selected_entry.non_canonical)
        or not (preview.snapshot.shipment_time_snapshot)
        or not preview.draft.preview_only
        or preview.draft.live_provider_write
        or preview.provider_call_performed
    ):
        return ("Unsafe runtime address book preview state",)

    return ()


def main() -> int:
    try:
        findings = run_validation()
    except (
        FileNotFoundError,
        OSError,
        ValueError,
        yaml.YAMLError,
    ) as exc:
        print(f"Test address book validation failed: {exc}")
        return 1

    print("ForPrint Logistics Service — test address book validation")
    print("")

    if findings:
        for finding in findings:
            print(f"[FAILED] {finding}")

        print("")
        print(f"Test address book validation failed: {len(findings)} error(s).")
        return 1

    print("[OK] Three local synthetic address book entries.")
    print("[OK] Alias and recipient reference lookup.")
    print("[OK] Shipment-time address snapshot.")
    print("[OK] Preview-only shipment draft without provider calls.")
    print("[OK] No real customer data, credentials or forbidden ownership.")
    print("[OK] Live provider writes remain disabled.")
    print("")
    print("Test address book validation passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
