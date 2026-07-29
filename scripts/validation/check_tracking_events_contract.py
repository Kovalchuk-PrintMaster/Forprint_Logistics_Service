from __future__ import annotations

from app.domain import ShipmentEventType
from scripts.previews.preview_tracking_events_contract import (
    DEFAULT_FIXTURE_PATH,
    REQUIRED_SAFETY_FLAGS,
    build_tracking_events_preview,
)


def main() -> int:
    try:
        preview = build_tracking_events_preview(DEFAULT_FIXTURE_PATH)
    except (OSError, ValueError) as exc:
        print(f"Tracking events contract validation failed: {exc}")
        return 1

    expected_event_types = {item.value for item in ShipmentEventType}
    actual_event_types = set(preview.event_types_seen)

    if actual_event_types != expected_event_types:
        print("Tracking events contract validation failed: canonical event taxonomy is incomplete")
        return 1

    scenario_ids = {str(item["scenario_id"]) for item in preview.scenarios}

    if scenario_ids != {
        "lifecycle_success",
        "provider_failure",
        "manual_attention",
    }:
        print(
            "Tracking events contract validation failed: "
            "required synthetic scenarios are incomplete"
        )
        return 1

    decisions = {
        observation["decision"]
        for scenario in preview.scenarios
        for observation in scenario["observations"]
    }

    if not {"accepted", "duplicate", "out_of_order"}.issubset(decisions):
        print(
            "Tracking events contract validation failed: "
            "duplicate or out-of-order evidence is missing"
        )
        return 1

    if preview.safety != REQUIRED_SAFETY_FLAGS:
        print("Tracking events contract validation failed: safety flags changed")
        return 1

    if not preview.notification_replay_stable:
        print("Tracking events contract validation failed: notification replay keys are unstable")
        return 1

    print("ForPrint Logistics Service — tracking events contract validation")
    print("")
    print("[OK] Six canonical provider-neutral event types.")
    print("[OK] Typed versioned event envelopes.")
    print("[OK] Deterministic lifecycle transitions.")
    print("[OK] Duplicate and out-of-order observations.")
    print("[OK] Failure and human-attention scenarios.")
    print("[OK] Channel-neutral notification projections.")
    print("[OK] Stable event and notification idempotency.")
    print("[OK] Synthetic fixture contains no credentials or real data.")
    print("[OK] Preview-only execution with no external calls or writes.")
    print("")
    print("Tracking events contract validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
