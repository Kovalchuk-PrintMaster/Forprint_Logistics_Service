import json

from scripts.previews.preview_provider_adapter_contract import (
    build_console_summary,
    build_preview_data,
    write_preview_artifact,
)


def test_preview_workflow_is_fully_non_live() -> None:
    data = build_preview_data()

    assert data["preview_only"] is True
    assert data["live_write"] is False
    assert data["provider_call_performed"] is False
    assert len(data["providers"]) == 4
    assert data["shipment_preview"]["provider_call_performed"] is False
    assert data["unsupported_tracking"]["provider_call_performed"] is False


def test_preview_artifact_is_created(
    tmp_path,
) -> None:
    data = build_preview_data()

    path = write_preview_artifact(
        data,
        tmp_path,
    )

    assert path.is_file()

    stored = json.loads(path.read_text(encoding="utf-8"))

    assert stored["schema_version"] == ("provider_adapter_contract_preview_v0_1")
    assert stored["live_write"] is False


def test_preview_console_uses_boxed_tables() -> None:
    output = build_console_summary(build_preview_data())

    assert "┌" in output
    assert "┐" in output
    assert "└" in output
    assert "synthetic_parcel" in output
    assert "Live shipment write" in output
    assert "DISABLED" in output
