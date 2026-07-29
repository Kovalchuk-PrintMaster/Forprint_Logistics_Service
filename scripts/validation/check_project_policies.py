from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]

LOCAL_OWNER_ADDRESS_BOOK_PATH = "runtime/address_book/owner_recipients.yaml"

FORBIDDEN_PLACEHOLDERS = (
    "{now}",
    "{branch}",
    "{commit}",
    "{module_id}",
    "{phase}",
    "{completed_step}",
    "{{now}}",
    "{{branch}}",
    "{{commit}}",
)

REQUIRED_PATHS = (
    "forprint_module_manifest.yaml",
    ".env.example",
    ".gitignore",
    "config/module.yaml",
    "config/providers.example.yaml",
    "coordination/status/current_status.yaml",
    "coordination/status/current_status.md",
    "coordination/status/next_questions_for_blueprint.md",
    "coordination/prompts/index.yaml",
    "coordination/reports/index.yaml",
    "examples/fixtures/recipients/test_recipients.yaml",
    "examples/fixtures/address_book/test_address_book.yaml",
    "examples/workflows/address_book_lookup_preview.yaml",
    "docs/architecture/adapters/provider_adapter_policy.md",
    "docs/architecture/boundaries/logistics_service_boundary.md",
    "docs/architecture/boundaries/test_address_book_boundary.md",
    "docs/development/configuration/secrets_policy.md",
    "docs/development/testing/local_test_data_policy.md",
    "docs/architecture/tracking_event_contract.md",
    "docs/architecture/boundaries/notification_handoff_boundary.md",
    "docs/operations/tracking_events_runbook.md",
    "docs/operations/tracking_events_recovery.md",
)

SENSITIVE_ENV_NAMES = (
    "FORPRINT_LOGISTICS_NOVA_POSHTA_API_KEY",
    "FORPRINT_LOGISTICS_UKRPOSHTA_API_TOKEN",
    "FORPRINT_LOGISTICS_MEEST_API_TOKEN",
    "FORPRINT_LOGISTICS_SAT_API_TOKEN",
)


@dataclass(frozen=True, slots=True)
class PolicyResult:
    name: str
    status: str
    details: str


def _load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _result(name: str, passed: bool, details: str) -> PolicyResult:
    return PolicyResult(
        name=name,
        status="OK" if passed else "FAILED",
        details=details,
    )


def _check_required_paths(root: Path) -> PolicyResult:
    missing = [path for path in REQUIRED_PATHS if not (root / path).is_file()]

    return _result(
        "Required project files",
        not missing,
        "All required files exist." if not missing else "Missing: " + ", ".join(missing),
    )


def _check_yaml_files(root: Path) -> PolicyResult:
    yaml_paths = (
        "forprint_module_manifest.yaml",
        "config/module.yaml",
        "config/providers.example.yaml",
        "coordination/blueprint_source.yaml",
        "coordination/prompts/index.yaml",
        "coordination/reports/index.yaml",
        "coordination/status/current_status.yaml",
        "examples/fixtures/recipients/test_recipients.yaml",
        "examples/fixtures/address_book/test_address_book.yaml",
        "examples/workflows/address_book_lookup_preview.yaml",
    )

    try:
        for relative_path in yaml_paths:
            _load_yaml(root / relative_path)
    except (OSError, yaml.YAMLError) as exc:
        return _result("YAML parsing", False, str(exc))

    return _result("YAML parsing", True, "All required YAML files are valid.")


def _check_manifest_boundary(root: Path) -> PolicyResult:
    manifest = _load_yaml(root / "forprint_module_manifest.yaml")

    passed = (
        manifest["module_id"] == "logistics_service"
        and "order" in manifest["responsibilities"]["must_not_own"]
        and "invoice" in manifest["responsibilities"]["must_not_own"]
    )

    return _result(
        "Manifest boundary",
        passed,
        "Canonical module id and forbidden ownership are declared.",
    )


def _check_live_write_disabled(root: Path) -> PolicyResult:
    module_config = _load_yaml(root / "config/module.yaml")
    provider_config = _load_yaml(root / "config/providers.example.yaml")

    providers_are_safe = all(
        provider["live_write_enabled"] is False for provider in provider_config["providers"]
    )

    passed = (
        module_config["features"]["live_provider_writes_enabled"] is False
        and provider_config["live_provider_writes_enabled"] is False
        and providers_are_safe
    )

    return _result(
        "Live provider write safety",
        passed,
        "All committed live-write flags are disabled.",
    )


def _check_fixture_boundary(root: Path) -> PolicyResult:
    fixture = _load_yaml(root / "examples/fixtures/recipients/test_recipients.yaml")

    recipients = fixture.get("recipients", [])

    passed = (
        fixture.get("non_canonical") is True
        and fixture.get("purpose") == "local logistics testing only"
        and recipients
        and all(item.get("non_canonical") is True for item in recipients)
    )

    return _result(
        "Non-canonical fixture",
        passed,
        "Recipient fixture is explicitly local and non-canonical.",
    )


def _check_address_book_fixture_boundary(
    root: Path,
) -> PolicyResult:
    fixture = _load_yaml(root / "examples/fixtures/address_book/test_address_book.yaml")

    if not isinstance(fixture, dict):
        return _result(
            "Synthetic address book fixture",
            False,
            "Fixture root must be a mapping.",
        )

    entries = fixture.get("entries", [])

    if not isinstance(entries, list):
        return _result(
            "Synthetic address book fixture",
            False,
            "Fixture entries must be a list.",
        )

    required_kinds = {
        "kyiv_local",
        "warehouse",
        "office",
    }
    actual_kinds: set[str] = set()
    entries_are_safe = True

    for entry in entries:
        if not isinstance(entry, dict):
            entries_are_safe = False
            continue

        actual_kinds.add(str(entry.get("entry_kind", "")))
        recipient = entry.get("recipient")

        if not isinstance(recipient, dict):
            entries_are_safe = False
            continue

        entries_are_safe = (
            entries_are_safe
            and entry.get("synthetic_data") is True
            and entry.get("real_customer_data") is False
            and entry.get("non_canonical") is True
            and entry.get("logistics_reference_only") is True
            and recipient.get("non_canonical") is True
            and recipient.get("phone") is None
            and str(
                recipient.get(
                    "recipient_ref",
                    "",
                )
            ).startswith("test_recipient_")
            and str(
                recipient.get(
                    "display_name",
                    "",
                )
            ).startswith("Synthetic ")
        )

    passed = (
        fixture.get("non_canonical") is True
        and fixture.get("preview_only") is True
        and fixture.get("live_provider_write") is False
        and fixture.get("synthetic_data") is True
        and fixture.get("real_customer_data") is False
        and len(entries) == 3
        and required_kinds == actual_kinds
        and entries_are_safe
    )

    return _result(
        "Synthetic address book fixture",
        passed,
        (
            "Committed address book entries are "
            "synthetic, non-canonical and free "
            "of private recipient data."
        ),
    )


def _check_env_example(root: Path) -> PolicyResult:
    values: dict[str, str] = {}

    for line in (root / ".env.example").read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue

        name, value = line.split("=", maxsplit=1)
        values[name] = value

    sensitive_values_are_empty = all(values.get(name) == "" for name in SENSITIVE_ENV_NAMES)

    passed = (
        values.get("FORPRINT_LOGISTICS_LIVE_PROVIDER_WRITES_ENABLED") == "false"
        and sensitive_values_are_empty
    )

    return _result(
        "Environment example safety",
        passed,
        "Provider credentials are empty and live writes are disabled.",
    )


def _check_flat_directory_policy(root: Path) -> PolicyResult:
    allowed_root_files = {
        "tests": {"__init__.py"},
        "scripts": {"__init__.py"},
        "docs": set(),
        "examples": set(),
    }

    unexpected: list[str] = []

    for directory_name, allowed_names in allowed_root_files.items():
        directory = root / directory_name

        for path in directory.iterdir():
            if path.is_file() and path.name not in allowed_names:
                unexpected.append(str(path.relative_to(root)))

    return _result(
        "Thematic directory layout",
        not unexpected,
        "General directories contain only approved root files."
        if not unexpected
        else "Unexpected root files: " + ", ".join(unexpected),
    )


def _check_coordination_placeholders(root: Path) -> PolicyResult:
    findings: list[str] = []
    coordination_root = root / "coordination"

    for path in coordination_root.rglob("*"):
        if not path.is_file() or path.suffix not in {".yaml", ".yml", ".md"}:
            continue

        text = path.read_text(encoding="utf-8")

        for token in FORBIDDEN_PLACEHOLDERS:
            if token in text:
                findings.append(f"{path.relative_to(root)}: {token}")

    return _result(
        "Coordination placeholders",
        not findings,
        "No unresolved coordination placeholders found."
        if not findings
        else "Found: " + ", ".join(findings),
    )


def _check_tracked_secret_files(root: Path) -> PolicyResult:
    completed = subprocess.run(
        ["git", "ls-files"],
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
    )

    if completed.returncode != 0:
        return _result(
            "Tracked secret files",
            False,
            completed.stderr.strip() or "git ls-files failed",
        )

    tracked = completed.stdout.splitlines()
    forbidden: list[str] = []

    for path in tracked:
        name = Path(path).name

        if name in {
            ".env",
            ".env.local",
            ".env.production",
        }:
            forbidden.append(path)

        if Path(path).suffix in {
            ".pem",
            ".key",
            ".p12",
            ".pfx",
        }:
            forbidden.append(path)

    return _result(
        "Tracked secret files",
        not forbidden,
        "No secret-like files are tracked."
        if not forbidden
        else "Tracked secret-like files: " + ", ".join(forbidden),
    )


def _check_local_owner_address_book_policy(
    root: Path,
) -> PolicyResult:
    ignored = subprocess.run(
        [
            "git",
            "check-ignore",
            "--quiet",
            "--",
            LOCAL_OWNER_ADDRESS_BOOK_PATH,
        ],
        cwd=root,
        check=False,
    )
    tracked = subprocess.run(
        [
            "git",
            "ls-files",
            "--error-unmatch",
            "--",
            LOCAL_OWNER_ADDRESS_BOOK_PATH,
        ],
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
    )
    tracked_directory = subprocess.run(
        [
            "git",
            "ls-files",
            "--",
            "runtime/address_book",
        ],
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
    )

    boundary_text = (root / "docs/architecture/boundaries/test_address_book_boundary.md").read_text(
        encoding="utf-8"
    )
    policy_text = (root / "docs/development/testing/local_test_data_policy.md").read_text(
        encoding="utf-8"
    )

    passed = (
        ignored.returncode == 0
        and tracked.returncode != 0
        and not tracked_directory.stdout.strip()
        and LOCAL_OWNER_ADDRESS_BOOK_PATH in boundary_text
        and LOCAL_OWNER_ADDRESS_BOOK_PATH in policy_text
    )

    return _result(
        "Local owner address book",
        passed,
        ("Owner-maintained recipient data uses a documented Git-ignored and untracked local path."),
    )


def run_policy_checks(root: Path = PROJECT_ROOT) -> list[PolicyResult]:
    return [
        _check_required_paths(root),
        _check_yaml_files(root),
        _check_manifest_boundary(root),
        _check_live_write_disabled(root),
        _check_fixture_boundary(root),
        _check_address_book_fixture_boundary(root),
        _check_env_example(root),
        _check_flat_directory_policy(root),
        _check_coordination_placeholders(root),
        _check_tracked_secret_files(root),
        _check_local_owner_address_book_policy(root),
    ]


def main() -> int:
    results = run_policy_checks()

    print("ForPrint Logistics Service — project policy check")
    print("")

    for result in results:
        print(f"[{result.status}] {result.name}: {result.details}")

    failed = [result for result in results if result.status == "FAILED"]

    if failed:
        print("")
        print(f"Project policy check failed: {len(failed)} error(s).")
        return 1

    print("")
    print("Project policy check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
