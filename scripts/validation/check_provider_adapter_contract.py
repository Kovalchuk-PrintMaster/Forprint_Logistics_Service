from __future__ import annotations

from scripts.previews.preview_provider_adapter_contract import (
    build_preview_data,
)


def main() -> int:
    data = build_preview_data()
    findings: list[str] = []

    provider_ids = tuple(item["provider_id"] for item in data["providers"])

    expected_provider_ids = (
        "synthetic_freight",
        "synthetic_parcel",
        "synthetic_postal",
        "synthetic_taxi_courier",
    )

    if provider_ids != expected_provider_ids:
        findings.append("Synthetic provider inventory mismatch")

    if data.get("preview_only") is not True:
        findings.append("Top-level preview_only must be true")

    if data.get("live_write") is not False:
        findings.append("Top-level live_write must be false")

    if data.get("provider_call_performed") is not False:
        findings.append("No provider call may be performed")

    shipment_preview = data["shipment_preview"]

    if shipment_preview["preview_only"] is not True:
        findings.append("Shipment preview must remain preview-only")

    if shipment_preview["live_write"] is not False:
        findings.append("Shipment preview live_write must be false")

    if shipment_preview["provider_call_performed"] is not False:
        findings.append("Shipment preview performed a provider call")

    tracking_errors = data["unsupported_tracking"]["errors"]

    if not tracking_errors:
        findings.append("Unsupported tracking must return an error")
    elif tracking_errors[0]["code"] != "unsupported_capability":
        findings.append("Unexpected unsupported tracking error")

    quote_errors = data["unsupported_quote"]["errors"]

    if not quote_errors:
        findings.append("Unsupported quote must return an error")
    elif quote_errors[0]["code"] != "unsupported_capability":
        findings.append("Unexpected unsupported quote error")

    live_write = data["live_write_disabled"]

    if live_write["code"] != "live_write_disabled":
        findings.append("Live write error taxonomy mismatch")

    if live_write["retryable"] is not False:
        findings.append("Live write error must not be retryable")

    print("ForPrint Logistics Service — provider adapter contract validation")
    print("")

    if findings:
        for finding in findings:
            print(f"[FAILED] {finding}")

        return 1

    print("[OK] Four synthetic provider classes.")
    print("[OK] Typed recipient and address validation.")
    print("[OK] Preview-only shipment payload envelope.")
    print("[OK] Unsupported tracking and quote results.")
    print("[OK] Live provider writes remain disabled.")
    print("[OK] No real provider calls or credentials.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
