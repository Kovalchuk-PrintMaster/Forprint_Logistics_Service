from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import yaml

REQUIRED_FIELDS = (
    "completion_id",
    "module_id",
    "module_name",
    "phase",
    "prompt_id",
    "report_id",
    "report_path",
    "created_at",
    "summary",
    "implemented",
    "checks",
    "instruction_sources_reviewed",
    "standards_reviewed",
    "standards_alignment_notes",
    "boundary_confirmation",
    "current_outputs",
    "next_recommended_steps",
    "next_questions_for_blueprint",
)

MODULE_REQUIRED_FIELDS = (
    "branch",
    "implementation_commit",
    "push_status",
)

REQUIRED_CHECKS = (
    "check_report",
    "tests",
    "governance_check",
)

SAFE_FALSE_BOUNDARY_FLAGS = (
    "production_api_added",
    "live_external_integrations_added",
    "database_ownership_added",
    "operational_data_ownership_added",
    "queue_or_cache_dependency_added",
    "one_c_writes_added",
    "automatic_posting_added",
    "final_price_calculation_added",
    "live_provider_writes_added",
    "real_provider_credentials_committed",
    "blueprint_repository_written_directly",
)

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

SUPPORTED_PUSH_STATUSES = {
    "not_pushed",
    "pushed",
    "no_remote",
    "push_failed",
}

COMMIT_PATTERN = re.compile(r"^[0-9a-f]{7,40}$")


def load_packet(packet_path: Path) -> dict[str, Any]:
    data = yaml.safe_load(packet_path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError("Completion packet root must be a YAML mapping")

    return data


def _find_placeholders(value: Any, location: str = "packet") -> list[str]:
    findings: list[str] = []

    if isinstance(value, str):
        for token in FORBIDDEN_PLACEHOLDERS:
            if token in value:
                findings.append(f"{location}: unresolved placeholder {token}")

    elif isinstance(value, dict):
        for key, child in value.items():
            findings.extend(_find_placeholders(child, f"{location}.{key}"))

    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_find_placeholders(child, f"{location}[{index}]"))

    return findings


def _require_non_empty_list(
    packet: dict[str, Any],
    field_name: str,
    errors: list[str],
) -> None:
    value = packet.get(field_name)

    if not isinstance(value, list) or not value:
        errors.append(f"{field_name} must be a non-empty list")


def validate_packet(packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    for field_name in (*REQUIRED_FIELDS, *MODULE_REQUIRED_FIELDS):
        if field_name not in packet:
            errors.append(f"Missing required field: {field_name}")

    if errors:
        return errors

    if packet["module_id"] != "logistics_service":
        errors.append("module_id must be logistics_service")

    for field_name in (
        "completion_id",
        "module_name",
        "phase",
        "prompt_id",
        "report_id",
        "report_path",
        "created_at",
        "summary",
        "branch",
        "implementation_commit",
        "push_status",
    ):
        value = packet.get(field_name)

        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field_name} must be a non-empty string")

    report_path = Path(packet["report_path"])

    if report_path.is_absolute():
        errors.append("report_path must be relative to the module repository")

    expected_prefix = ("coordination", "reports", "completion")

    if report_path.parts[:3] != expected_prefix:
        errors.append("report_path must be under coordination/reports/completion/")

    if report_path.suffix != ".md":
        errors.append("report_path must point to a Markdown file")

    implementation_commit = packet["implementation_commit"]

    if not COMMIT_PATTERN.fullmatch(implementation_commit):
        errors.append("implementation_commit must contain a real 7-40 character lowercase Git hash")

    if packet["push_status"] not in SUPPORTED_PUSH_STATUSES:
        errors.append("push_status must be one of: " + ", ".join(sorted(SUPPORTED_PUSH_STATUSES)))

    for field_name in (
        "implemented",
        "instruction_sources_reviewed",
        "standards_reviewed",
        "standards_alignment_notes",
        "current_outputs",
        "next_recommended_steps",
    ):
        _require_non_empty_list(packet, field_name, errors)

    questions = packet.get("next_questions_for_blueprint")

    if not isinstance(questions, list):
        errors.append("next_questions_for_blueprint must be a list")

    checks = packet.get("checks")

    if not isinstance(checks, dict):
        errors.append("checks must be a mapping")
    else:
        for check_name in REQUIRED_CHECKS:
            if checks.get(check_name) != "ok":
                errors.append(f"checks.{check_name} must be 'ok'")

    boundary = packet.get("boundary_confirmation")

    if not isinstance(boundary, dict):
        errors.append("boundary_confirmation must be a mapping")
    else:
        for flag_name in SAFE_FALSE_BOUNDARY_FLAGS:
            if flag_name not in boundary:
                errors.append(f"Missing boundary_confirmation flag: {flag_name}")
            elif boundary[flag_name] is not False:
                errors.append(f"boundary_confirmation.{flag_name} must be false")

    errors.extend(_find_placeholders(packet))

    return errors


def validate_packet_path(packet_path: Path) -> list[str]:
    try:
        packet = load_packet(packet_path)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return [str(exc)]

    return validate_packet(packet)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Logistics Service completion packet.")
    parser.add_argument("packet", type=Path)
    args = parser.parse_args()

    errors = validate_packet_path(args.packet)

    if errors:
        print("Completion packet validation failed:")

        for error in errors:
            print(f"  - {error}")

        return 1

    print(f"Completion packet is valid: {args.packet}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
