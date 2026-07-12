from __future__ import annotations

from scripts.previews.preview_local_logistics_model import (
    DEFAULT_EXAMPLES_ROOT,
    EXAMPLE_FILENAMES,
    build_local_model_preview,
)


def main() -> int:
    try:
        preview = build_local_model_preview(DEFAULT_EXAMPLES_ROOT)
    except (
        FileNotFoundError,
        OSError,
        ValueError,
    ) as exc:
        print(f"Local model example validation failed: {exc}")
        return 1

    print("ForPrint Logistics Service — local model examples")
    print("")

    for filename in EXAMPLE_FILENAMES:
        print(f"[OK] {filename}")

    print("")
    print("[OK] Safety flags: non-canonical, preview-only and no live provider write.")
    print("[OK] Shipment, tracking and notification references are consistent.")
    print("[OK] Local repository flow built without provider API calls.")
    print(f"[OK] Tracking events: {len(preview.tracking_events)}")
    print("")
    print("Local model example validation passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
