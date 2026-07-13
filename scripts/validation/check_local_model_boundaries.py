from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from scripts.previews.preview_local_logistics_model import (
    EXAMPLE_FILENAMES,
    build_local_model_preview,
    load_workflow_examples,
)
from scripts.validation.check_test_address_book import (
    run_validation as run_test_address_book_validation,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_PATHS = (
    "app/domain/address_book.py",
    "app/domain/events.py",
    "app/domain/providers.py",
    "app/domain/recipients.py",
    "app/domain/shipments.py",
    "app/domain/tracking.py",
    "app/services/address_book_service.py",
    "app/services/notification_event_service.py",
    "app/services/shipment_draft_service.py",
    "app/services/tracking_event_service.py",
    "app/storage/in_memory.py",
    "app/storage/repositories.py",
    "examples/fixtures/address_book/test_address_book.yaml",
    "examples/workflows/address_book_lookup_preview.yaml",
    "examples/workflows/shipment_draft_preview.yaml",
    "examples/workflows/tracking_request_preview.yaml",
    "examples/workflows/notification_event_preview.yaml",
    "scripts/previews/preview_local_logistics_model.py",
    "scripts/previews/preview_test_address_book.py",
    "scripts/validation/check_test_address_book.py",
    "docs/architecture/boundaries/local_logistics_model_boundary.md",
    "docs/architecture/boundaries/test_address_book_boundary.md",
    "docs/development/testing/local_logistics_model_preview.md",
    "docs/development/testing/local_test_data_policy.md",
)

SCANNED_PYTHON_DIRECTORIES = (
    "app/services",
    "app/storage",
    "scripts/previews",
    "scripts/validation",
)

FORBIDDEN_IMPORT_PREFIXES = (
    "app.adapters",
    "fastapi",
    "httpx",
    "requests",
    "sqlite3",
    "urllib",
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


@dataclass(frozen=True, slots=True)
class BoundaryCheckResult:
    name: str
    status: str
    details: str


def result(
    name: str,
    passed: bool,
    details: str,
) -> BoundaryCheckResult:
    return BoundaryCheckResult(
        name=name,
        status="OK" if passed else "FAILED",
        details=details,
    )


def module_is_forbidden(module_name: str) -> bool:
    return any(
        module_name == prefix or module_name.startswith(prefix + ".")
        for prefix in FORBIDDEN_IMPORT_PREFIXES
    )


def find_forbidden_imports(
    root: Path,
) -> tuple[str, ...]:
    findings: list[str] = []

    for relative_directory in SCANNED_PYTHON_DIRECTORIES:
        directory = root / relative_directory

        if not directory.is_dir():
            continue

        for path in sorted(directory.rglob("*.py")):
            try:
                tree = ast.parse(
                    path.read_text(encoding="utf-8"),
                    filename=str(path),
                )
            except (OSError, SyntaxError) as exc:
                findings.append(f"{path.relative_to(root)}: cannot parse: {exc}")
                continue

            for node in ast.walk(tree):
                modules: tuple[str, ...] = ()

                if isinstance(node, ast.Import):
                    modules = tuple(alias.name for alias in node.names)
                elif isinstance(
                    node,
                    ast.ImportFrom,
                ):
                    modules = (node.module or "",)

                for module_name in modules:
                    if module_is_forbidden(module_name):
                        findings.append(f"{path.relative_to(root)}:{node.lineno}: {module_name}")

    return tuple(findings)


def find_sensitive_keys(
    value: object,
    *,
    location: str = "root",
) -> tuple[str, ...]:
    findings: list[str] = []

    if isinstance(value, dict):
        for raw_key, child in value.items():
            key = str(raw_key)
            normalized_key = key.strip().lower()
            child_location = f"{location}.{key}"

            if normalized_key in SENSITIVE_KEY_NAMES:
                findings.append(child_location)

            findings.extend(
                find_sensitive_keys(
                    child,
                    location=child_location,
                )
            )

    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(
                find_sensitive_keys(
                    child,
                    location=(f"{location}[{index}]"),
                )
            )

    return tuple(findings)


def validate_workflow_safety_data(
    filename: str,
    data: dict[str, Any],
) -> tuple[str, ...]:
    findings: list[str] = []

    if data.get("non_canonical") is not True:
        findings.append(f"{filename}: non_canonical must be true")

    if data.get("preview_only") is not True:
        findings.append(f"{filename}: preview_only must be true")

    if data.get("live_provider_write") is not False:
        findings.append(f"{filename}: live_provider_write must be false")

    if filename == "shipment_draft_preview.yaml":
        recipient = data.get("recipient", {})
        destination = data.get(
            "destination",
            {},
        )

        if not isinstance(recipient, dict) or recipient.get("non_canonical") is not True:
            findings.append(f"{filename}: recipient must remain non-canonical")

        if (
            not isinstance(destination, dict)
            or destination.get("shipment_time_snapshot") is not True
        ):
            findings.append(f"{filename}: destination must be a shipment-time snapshot")

    if filename == "tracking_request_preview.yaml":
        request = data.get(
            "tracking_request",
            {},
        )
        events = data.get(
            "tracking_events",
            [],
        )

        if not isinstance(request, dict) or request.get("local_only") is not True:
            findings.append(f"{filename}: tracking request must remain local-only")

        if not isinstance(request, dict) or request.get("provider_call_performed") is not False:
            findings.append(f"{filename}: provider call must not be performed")

        if (
            not isinstance(events, list)
            or not events
            or any(
                not isinstance(event, dict) or event.get("local_record") is not True
                for event in events
            )
        ):
            findings.append(f"{filename}: tracking events must remain local records")

    if filename == "notification_event_preview.yaml":
        notification = data.get(
            "notification_event",
            {},
        )

        if not isinstance(notification, dict) or notification.get("local_payload") is not True:
            findings.append(f"{filename}: notification must remain a local payload")

        if (
            not isinstance(notification, dict)
            or notification.get("delivery_performed") is not False
        ):
            findings.append(f"{filename}: notification delivery must remain disabled")

    sensitive_keys = find_sensitive_keys(
        data,
        location=filename,
    )

    findings.extend(f"{filename}: sensitive key found: {key}" for key in sensitive_keys)

    return tuple(findings)


def check_required_paths(
    root: Path,
) -> BoundaryCheckResult:
    missing = [path for path in REQUIRED_PATHS if not (root / path).is_file()]

    return result(
        "Required local model files",
        not missing,
        (
            "All required implementation, example and documentation files exist."
            if not missing
            else "Missing: " + ", ".join(missing)
        ),
    )


def check_external_import_boundary(
    root: Path,
) -> BoundaryCheckResult:
    findings = find_forbidden_imports(root)

    return result(
        "External dependency boundary",
        not findings,
        (
            "No provider adapters, HTTP clients, "
            "SQLite clients or API frameworks are "
            "imported by the local model layers."
            if not findings
            else "Found: " + ", ".join(findings)
        ),
    )


def check_workflow_safety(
    root: Path,
) -> BoundaryCheckResult:
    examples_root = root / "examples/workflows"

    try:
        examples = load_workflow_examples(examples_root)
    except (
        FileNotFoundError,
        OSError,
        ValueError,
        yaml.YAMLError,
    ) as exc:
        return result(
            "Workflow safety",
            False,
            str(exc),
        )

    findings: list[str] = []

    for filename in EXAMPLE_FILENAMES:
        findings.extend(
            validate_workflow_safety_data(
                filename,
                examples[filename],
            )
        )

    return result(
        "Workflow safety",
        not findings,
        (
            "All local workflow examples retain safe ownership and execution flags."
            if not findings
            else "Found: " + ", ".join(findings)
        ),
    )


def check_runtime_preview(
    root: Path,
) -> BoundaryCheckResult:
    try:
        preview = build_local_model_preview(root / "examples/workflows")
    except (
        FileNotFoundError,
        OSError,
        ValueError,
        yaml.YAMLError,
    ) as exc:
        return result(
            "Runtime local model",
            False,
            str(exc),
        )

    passed = (
        preview.recipient.non_canonical
        and preview.draft.preview_only
        and not preview.draft.live_provider_write
        and preview.tracking_request.local_only
        and not (preview.tracking_request.provider_call_performed)
        and all(event.local_record for event in preview.tracking_events)
        and preview.notification.local_payload
        and not (preview.notification.delivery_performed)
    )

    return result(
        "Runtime local model",
        passed,
        (
            "Complete local workflow builds in memory without external calls."
            if passed
            else "Unsafe runtime state detected."
        ),
    )


def check_test_address_book_boundary(
    root: Path,
) -> BoundaryCheckResult:
    try:
        findings = run_test_address_book_validation(
            root / "examples/fixtures/address_book/test_address_book.yaml",
            root / "examples/workflows/address_book_lookup_preview.yaml",
        )
    except (
        FileNotFoundError,
        OSError,
        ValueError,
        yaml.YAMLError,
    ) as exc:
        return result(
            "Test address book boundary",
            False,
            str(exc),
        )

    return result(
        "Test address book boundary",
        not findings,
        (
            "Synthetic address book lookup, "
            "snapshot and shipment preview "
            "remain local and non-canonical."
            if not findings
            else "Found: " + ", ".join(findings)
        ),
    )


def run_boundary_checks(
    root: Path = PROJECT_ROOT,
) -> list[BoundaryCheckResult]:
    return [
        check_required_paths(root),
        check_external_import_boundary(root),
        check_workflow_safety(root),
        check_runtime_preview(root),
        check_test_address_book_boundary(root),
    ]


def main() -> int:
    results = run_boundary_checks()

    print("ForPrint Logistics Service — local model boundary check")
    print("")

    for item in results:
        print(f"[{item.status}] {item.name}: {item.details}")

    failed = [item for item in results if item.status == "FAILED"]

    print("")

    if failed:
        print(f"Local model boundary check failed: {len(failed)} error(s).")
        return 1

    print("Local model boundary check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
