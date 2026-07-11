from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]

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
    "config/module.yaml",
    "config/providers.example.yaml",
    "coordination/status/current_status.yaml",
    "coordination/status/current_status.md",
    "coordination/status/next_questions_for_blueprint.md",
    "coordination/prompts/index.yaml",
    "coordination/reports/index.yaml",
    "examples/fixtures/recipients/test_recipients.yaml",
    "docs/architecture/adapters/provider_adapter_policy.md",
    "docs/architecture/boundaries/logistics_service_boundary.md",
    "docs/development/configuration/secrets_policy.md",
    "docs/development/testing/local_test_data_policy.md",
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


def run_policy_checks(root: Path = PROJECT_ROOT) -> list[PolicyResult]:
    return [
        _check_required_paths(root),
        _check_yaml_files(root),
        _check_manifest_boundary(root),
        _check_live_write_disabled(root),
        _check_fixture_boundary(root),
        _check_env_example(root),
        _check_flat_directory_policy(root),
        _check_coordination_placeholders(root),
        _check_tracked_secret_files(root),
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
