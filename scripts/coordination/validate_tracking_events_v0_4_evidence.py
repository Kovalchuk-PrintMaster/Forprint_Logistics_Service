from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "coordination/evidence/tracking_events_v0_4/source_obligation_audit.yaml"
TELEGRAM = ROOT / "coordination/evidence/tracking_events_v0_4/telegram_handoff.yaml"
CATALOG = ROOT / "coordination/evidence/tracking_events_v0_4/required_test_catalog.yaml"


def load(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected YAML mapping: {path}")
    return data


def validate() -> list[str]:
    errors: list[str] = []

    for path in (AUDIT, TELEGRAM, CATALOG):
        if not path.is_file():
            errors.append(f"missing evidence file: {path.relative_to(ROOT)}")

    if errors:
        return errors

    audit = load(AUDIT)
    rows = audit.get("source_obligations")
    if not isinstance(rows, list) or len(rows) != 26:
        errors.append("source_obligations must contain exactly 26 rows")
    else:
        ids = [row.get("source_obligation_id") for row in rows if isinstance(row, dict)]
        if len(ids) != len(set(ids)):
            errors.append("source obligation ids must be unique")
        if any(row.get("remaining_gap") is not False for row in rows if isinstance(row, dict)):
            errors.append("all source obligations must have remaining_gap=false")
        for row in rows:
            if not isinstance(row, dict):
                errors.append("source obligation row must be a mapping")
                continue
            if row.get("audit_status") not in {
                "SATISFIED_EXISTING",
                "EVIDENCE_GAP",
                "IMPLEMENTATION_GAP",
                "NOT_APPLICABLE_WITH_JUSTIFICATION",
            }:
                errors.append(f"invalid audit_status: {row.get('source_obligation_id')}")
            targets = (
                row.get("implementation_obligations", [])
                + row.get("verification_obligations", [])
                + row.get("completion_evidence_obligations", [])
            )
            if not targets:
                errors.append(
                    f"source obligation has no target mapping: {row.get('source_obligation_id')}"
                )

    telegram = load(TELEGRAM)
    examples = telegram.get("examples_by_event_type")
    expected = {
        "shipment_created",
        "tracking_updated",
        "arrived",
        "delivered",
        "failed",
        "needs_attention",
    }
    if not isinstance(examples, dict) or set(examples) != expected:
        errors.append("Telegram handoff must contain examples for all six event types")
    if telegram.get("event_type_coverage") != "6/6":
        errors.append("Telegram handoff event_type_coverage must be 6/6")
    safety = telegram.get("safety", {})
    for key, expected_value in {
        "preview_only": True,
        "live_write": False,
        "provider_call_performed": False,
        "Telegram_API_call": False,
        "cross_repository_write": False,
        "credentials_added": False,
    }.items():
        if safety.get(key) is not expected_value:
            errors.append(f"Telegram handoff safety.{key} mismatch")

    catalog = load(CATALOG)
    focused = catalog.get("focused_test_paths")
    if not isinstance(focused, list) or not focused:
        errors.append("required test catalog must contain focused_test_paths")

    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    preview_block = makefile.split("tracking-events-preview:", 1)[1].split(
        ".PHONY: tracking-events-preview-generate", 1
    )[0]
    if "--no-write" not in preview_block:
        errors.append("tracking-events-preview Make target is not read-only")
    if "tracking-events-preview-generate:" not in makefile:
        errors.append("explicit preview generation target is missing")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    errors = validate()

    print("ForPrint Tracking Events v0.4 evidence validation")
    print(f"result: {'PASSED' if not errors else 'FAILED'}")
    print("source_obligations: 26" if not errors else "source_obligations: INVALID")
    print("telegram_event_examples: 6/6" if not errors else "telegram_event_examples: INVALID")
    print(
        "tracking_events_preview_read_only: true"
        if not errors
        else "tracking_events_preview_read_only: false"
    )

    if errors:
        for error in errors:
            print(f"- {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
