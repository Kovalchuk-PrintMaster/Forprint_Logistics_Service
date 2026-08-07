from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import yaml

CURRENT_PACKET_SCHEMA = "module_completion_packet_v0_2"
CURRENT_INTAKE_PROTOCOL = "blueprint_completion_intake_v0_2"

REQUIRED_FIELDS = (
    "schema_version",
    "protocol_version",
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
    "branch",
    "implementation_commit",
    "push_status",
)

REQUIRED_CHECKS = ("check_report", "tests", "governance_check")
REQUIRED_BOUNDARY_FLAGS = (
    "no_production_api",
    "no_live_external_integrations",
    "no_real_1c_sync",
    "no_production_write",
    "no_automatic_posting",
)

SUPPORTED_PUSH_STATUSES = {"pushed", "synced", "remote"}
FULL_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
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


def _require_non_empty_list(packet: dict[str, Any], name: str, errors: list[str]) -> None:
    value = packet.get(name)
    if not isinstance(value, list) or not value:
        errors.append(f"{name} must be a non-empty list")


def validate_packet(packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for name in REQUIRED_FIELDS:
        if name not in packet:
            errors.append(f"Missing required field: {name}")
    if errors:
        return errors

    if packet["schema_version"] != CURRENT_PACKET_SCHEMA:
        errors.append(f"schema_version must be {CURRENT_PACKET_SCHEMA}")
    if packet["protocol_version"] != CURRENT_INTAKE_PROTOCOL:
        errors.append(f"protocol_version must be {CURRENT_INTAKE_PROTOCOL}")
    if packet["module_id"] != "logistics_service":
        errors.append("module_id must be logistics_service")

    for name in (
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
        value = packet.get(name)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{name} must be a non-empty string")

    report_path = Path(packet["report_path"])
    if report_path.is_absolute():
        errors.append("report_path must be relative to the module repository")
    if report_path.parts[:3] != ("coordination", "reports", "completion"):
        errors.append("report_path must be under coordination/reports/completion/")
    if report_path.suffix != ".md":
        errors.append("report_path must point to a Markdown file")

    implementation_commit = packet["implementation_commit"]
    if (
        not isinstance(implementation_commit, str)
        or FULL_COMMIT_PATTERN.fullmatch(implementation_commit) is None
    ):
        errors.append("implementation_commit must be a full 40-character lowercase Git hash")

    if packet["push_status"] not in SUPPORTED_PUSH_STATUSES:
        errors.append("push_status must be one of: pushed, remote, synced")

    for name in (
        "implemented",
        "instruction_sources_reviewed",
        "standards_reviewed",
        "standards_alignment_notes",
        "current_outputs",
        "next_recommended_steps",
    ):
        _require_non_empty_list(packet, name, errors)

    if not isinstance(packet.get("next_questions_for_blueprint"), list):
        errors.append("next_questions_for_blueprint must be a list")

    for field_name in (
        "next_questions_for_blueprint",
        "blockers",
        "dependency_implications",
    ):
        if not isinstance(packet.get(field_name), list):
            errors.append(f"{field_name} must be a list")

    checks = packet.get("checks")
    if not isinstance(checks, dict):
        errors.append("checks must be a mapping")
    else:
        for name in REQUIRED_CHECKS:
            if checks.get(name) != "ok":
                errors.append(f"checks.{name} must be 'ok'")
        for counter in ("check_report_failed", "check_report_warnings"):
            value = checks.get(counter)
            if value is not None and (not isinstance(value, int) or isinstance(value, bool)):
                errors.append(f"checks.{counter} must be an integer when present")
        if isinstance(checks.get("check_report_failed"), int) and checks["check_report_failed"] > 0:
            errors.append("checks.check_report_failed must be 0")

    boundary = packet.get("boundary_confirmation")
    if not isinstance(boundary, dict):
        errors.append("boundary_confirmation must be a mapping")
    else:
        for name in REQUIRED_BOUNDARY_FLAGS:
            if name not in boundary:
                errors.append(f"Missing boundary_confirmation flag: {name}")
            elif boundary[name] is not True:
                errors.append(f"boundary_confirmation.{name} must be true")
        for name, value in boundary.items():
            if name.startswith("no_") and value is not True:
                errors.append(f"boundary_confirmation.{name} must be true")
            elif (
                name.endswith(("_added", "_committed", "_written_directly")) and value is not False
            ):
                errors.append(f"boundary_confirmation.{name} must be false")

    supersedes = packet.get("supersedes_completion_id")
    reason = packet.get("revision_reason")
    if (supersedes is None) != (reason is None):
        errors.append("supersedes_completion_id and revision_reason must be provided together")
    if supersedes is not None and (not isinstance(supersedes, str) or not supersedes.strip()):
        errors.append("supersedes_completion_id must be a non-empty string")
    if reason is not None and (not isinstance(reason, str) or not reason.strip()):
        errors.append("revision_reason must be a non-empty string")
    if supersedes is not None and supersedes == packet["completion_id"]:
        errors.append("supersedes_completion_id must differ from completion_id")

    errors.extend(_find_placeholders(packet))
    return errors


def validate_packet_path(packet_path: Path) -> list[str]:
    try:
        packet = load_packet(packet_path)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return [str(exc)]
    return validate_packet(packet)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a current Logistics Service v0.2 completion packet."
    )
    parser.add_argument("packet", type=Path)
    args = parser.parse_args()
    errors = validate_packet_path(args.packet)
    if errors:
        print("Completion packet validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(
        "Completion packet is valid under "
        f"{CURRENT_PACKET_SCHEMA} / {CURRENT_INTAKE_PROTOCOL}: {args.packet}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
