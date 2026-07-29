from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from app.domain import (
    LogisticsNotificationProjection,
    ProviderTrackingObservation,
    ShipmentEventEnvelope,
    ShipmentEventType,
    TrackingProcessingDecision,
)
from app.services import TrackingContractService

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE_PATH = (
    PROJECT_ROOT / "examples/fixtures/tracking_events/synthetic_tracking_events.yaml"
)
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "reports/previews/tracking_events_contract_preview.json"

REQUIRED_SAFETY_FLAGS = {
    "preview_only": True,
    "live_write": False,
    "provider_call_performed": False,
    "telegram_api_call_performed": False,
    "cross_repository_write": False,
}


@dataclass(frozen=True, slots=True)
class TrackingEventsPreview:
    """Deterministic preview result without persistence or external calls."""

    fixture_id: str
    scenarios: tuple[dict[str, Any], ...]
    event_types_seen: tuple[str, ...]
    notification_replay_stable: bool
    safety: dict[str, bool]

    def to_mapping(self) -> dict[str, Any]:
        return {
            "fixture_id": self.fixture_id,
            "scenarios": list(self.scenarios),
            "event_types_seen": list(self.event_types_seen),
            "notification_replay_stable": self.notification_replay_stable,
            "safety": dict(self.safety),
        }


def load_fixture(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError("Tracking-events fixture root must be a mapping")

    return data


def parse_datetime(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("occurred_at must be an ISO datetime string")

    parsed = datetime.fromisoformat(value)

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("occurred_at must be timezone-aware")

    return parsed


def validate_fixture_safety(data: dict[str, Any]) -> None:
    if data.get("synthetic_data") is not True:
        raise ValueError("synthetic_data must be true")

    if data.get("real_customer_data") is not False:
        raise ValueError("real_customer_data must be false")

    for field_name, expected in REQUIRED_SAFETY_FLAGS.items():
        if data.get(field_name) is not expected:
            raise ValueError(f"{field_name} must be {str(expected).lower()}")

    serialized = json.dumps(data, ensure_ascii=False).casefold()
    forbidden_markers = (
        "api_key",
        "api_token",
        "access_token",
        "authorization",
        "credential",
        "password",
        "secret",
        "raw_response",
        "+380",
    )

    findings = [marker for marker in forbidden_markers if marker in serialized]

    if findings:
        raise ValueError("Fixture contains forbidden sensitive markers: " + ", ".join(findings))


def _build_observation(
    scenario: dict[str, Any],
    raw: dict[str, Any],
) -> ProviderTrackingObservation:
    return ProviderTrackingObservation(
        shipment_reference=str(scenario["shipment_reference"]),
        provider_id=str(scenario["provider_id"]),
        provider_status=str(raw["provider_status"]),
        occurred_at=parse_datetime(raw["occurred_at"]),
        tracking_reference=str(scenario["tracking_reference"]),
        provider_event_code=str(raw["provider_event_code"]),
        safe_metadata=(
            ("fixture", "synthetic_tracking_events_v0_1"),
            ("scenario_id", str(scenario["scenario_id"])),
        ),
        preview_only=True,
        live_write=False,
        provider_call_performed=False,
        telegram_api_call_performed=False,
        cross_repository_write=False,
    )


def _projection_replay_is_stable(
    event: ShipmentEventEnvelope,
    recipient_reference: str,
) -> bool:
    first = LogisticsNotificationProjection.from_event(
        event,
        recipient_reference=recipient_reference,
    )
    second = LogisticsNotificationProjection.from_event(
        event,
        recipient_reference=recipient_reference,
    )

    return (
        first.notification_key == second.notification_key
        and first.idempotency_key == second.idempotency_key
        and first.to_json() == second.to_json()
    )


def build_tracking_events_preview(
    fixture_path: Path = DEFAULT_FIXTURE_PATH,
) -> TrackingEventsPreview:
    data = load_fixture(fixture_path)
    validate_fixture_safety(data)

    scenarios = data.get("scenarios")

    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("scenarios must be a non-empty list")

    service = TrackingContractService()
    scenario_outputs: list[dict[str, Any]] = []
    event_types_seen: set[str] = set()
    replay_checks: list[bool] = []

    for raw_scenario in scenarios:
        if not isinstance(raw_scenario, dict):
            raise ValueError("Each scenario must be a mapping")

        raw_observations = raw_scenario.get("observations")

        if not isinstance(raw_observations, list) or not raw_observations:
            raise ValueError("Scenario observations must be a non-empty list")

        history: list[ShipmentEventEnvelope] = []
        observation_outputs: list[dict[str, Any]] = []

        for raw_observation in raw_observations:
            if not isinstance(raw_observation, dict):
                raise ValueError("Each observation must be a mapping")

            observation = _build_observation(
                raw_scenario,
                raw_observation,
            )
            result = service.process_observation(
                observation,
                correlation_id=str(raw_scenario["correlation_id"]),
                history=tuple(history),
                recipient_reference=str(raw_scenario["recipient_reference"]),
            )

            expected_decision = TrackingProcessingDecision(
                str(raw_observation["expected_decision"])
            )

            if result.decision is not expected_decision:
                raise ValueError(
                    f"{raw_scenario['scenario_id']}/"
                    f"{raw_observation['observation_id']}: "
                    f"expected {expected_decision.value}, "
                    f"got {result.decision.value}"
                )

            output: dict[str, Any] = {
                "observation_id": str(raw_observation["observation_id"]),
                "decision": result.decision.value,
                "reason_code": result.reason_code,
                "event": (
                    result.event.to_mapping()
                    if result.accepted and result.event is not None
                    else None
                ),
                "notification": (
                    result.notification.to_mapping() if result.notification is not None else None
                ),
            }

            if result.accepted:
                if result.event is None or result.notification is None:
                    raise ValueError("Accepted observation must emit event and notification")

                expected_event_type = ShipmentEventType(str(raw_observation["expected_event_type"]))

                if result.event.event_type is not expected_event_type:
                    raise ValueError(
                        f"Expected event type {expected_event_type.value}, "
                        f"got {result.event.event_type.value}"
                    )

                history.append(result.event)
                event_types_seen.add(result.event.event_type.value)
                replay_checks.append(
                    _projection_replay_is_stable(
                        result.event,
                        str(raw_scenario["recipient_reference"]),
                    )
                )

            observation_outputs.append(output)

        scenario_outputs.append(
            {
                "scenario_id": str(raw_scenario["scenario_id"]),
                "shipment_reference": str(raw_scenario["shipment_reference"]),
                "accepted_event_count": len(history),
                "observations": observation_outputs,
            }
        )

    return TrackingEventsPreview(
        fixture_id=str(data["fixture_id"]),
        scenarios=tuple(scenario_outputs),
        event_types_seen=tuple(sorted(event_types_seen)),
        notification_replay_stable=bool(replay_checks) and all(replay_checks),
        safety=dict(REQUIRED_SAFETY_FLAGS),
    )


def render_console(preview: TrackingEventsPreview) -> str:
    rows = [
        ("Fixture", preview.fixture_id),
        ("Scenarios", str(len(preview.scenarios))),
        ("Event types", ", ".join(preview.event_types_seen)),
        (
            "Notification replay",
            "STABLE" if preview.notification_replay_stable else "FAILED",
        ),
        ("Preview only", str(preview.safety["preview_only"]).lower()),
        ("Live write", str(preview.safety["live_write"]).lower()),
        (
            "Provider call",
            str(preview.safety["provider_call_performed"]).lower(),
        ),
        (
            "Telegram API call",
            str(preview.safety["telegram_api_call_performed"]).lower(),
        ),
        (
            "Cross-repository write",
            str(preview.safety["cross_repository_write"]).lower(),
        ),
    ]

    label_width = max(len(label) for label, _value in rows)
    value_width = max(len(value) for _label, value in rows)

    top = "┌" + "─" * (label_width + 2) + "┬" + "─" * (value_width + 2) + "┐"
    middle = "├" + "─" * (label_width + 2) + "┼" + "─" * (value_width + 2) + "┤"
    bottom = "└" + "─" * (label_width + 2) + "┴" + "─" * (value_width + 2) + "┘"

    lines = [
        "ForPrint Logistics Service — tracking events preview",
        "",
        top,
        f"│ {'Item'.ljust(label_width)} │ {'Value'.ljust(value_width)} │",
        middle,
    ]

    for label, value in rows:
        lines.append(f"│ {label.ljust(label_width)} │ {value.ljust(value_width)} │")

    lines.extend(
        [
            bottom,
            "",
            "No provider, Telegram or cross-repository call was performed.",
        ]
    )

    return "\n".join(lines)


def write_preview(
    preview: TrackingEventsPreview,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            preview.to_mapping(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=("Preview provider-neutral tracking events and channel-neutral notifications.")
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=DEFAULT_FIXTURE_PATH,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
    )
    args = parser.parse_args()

    try:
        preview = build_tracking_events_preview(args.fixture)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"Tracking events preview failed: {exc}")
        return 1

    print(render_console(preview))

    if not args.no_write:
        write_preview(preview, args.output)
        print("")
        print("Preview artifact: " + str(args.output.relative_to(PROJECT_ROOT)))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
