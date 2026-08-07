from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.coordination.validate_completion_packet import (  # noqa: E402, I001
    load_packet,
    validate_packet,
)


def _frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("Completion report must start with YAML frontmatter")
    parts = text.split("---", maxsplit=2)
    if len(parts) < 3:
        raise ValueError("Completion report frontmatter is not closed")
    data = yaml.safe_load(parts[1])
    if not isinstance(data, dict):
        raise ValueError("Completion report frontmatter must be a mapping")
    return data


def validate_report(packet: dict[str, Any], report_path: Path) -> list[str]:
    errors = validate_packet(packet)
    if errors:
        return ["Packet is invalid", *errors]
    try:
        data = _frontmatter(report_path)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return [str(exc)]
    expected = {
        "schema_version": packet["schema_version"],
        "protocol_version": packet["protocol_version"],
        "report_id": packet["report_id"],
        "prompt_id": packet["prompt_id"],
        "phase": packet["phase"],
        "completed_step": packet["completion_id"],
        "implementation_commit": packet["implementation_commit"],
        "branch": packet["branch"],
        "push_status": packet["push_status"],
        "supersedes_completion_id": packet.get("supersedes_completion_id"),
        "revision_reason": packet.get("revision_reason"),
        "boundary_confirmation": packet["boundary_confirmation"],
        "blueprint_review_status": "not_started",
        "automatic_acceptance": False,
    }
    for key, value in expected.items():
        if data.get(key) != value:
            errors.append(f"report frontmatter {key} does not match packet")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Logistics completion report/packet consistency."
    )
    parser.add_argument("packet", type=Path)
    args = parser.parse_args()
    packet = load_packet(args.packet)
    report_path = Path(packet["report_path"])
    if not report_path.is_absolute():
        report_path = Path.cwd() / report_path
    errors = validate_report(packet, report_path)
    if errors:
        print("Completion report validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"Completion report is consistent with packet: {args.packet}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
