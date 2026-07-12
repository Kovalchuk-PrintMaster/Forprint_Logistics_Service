from pathlib import Path

from scripts.validation.check_local_model_boundaries import (
    find_forbidden_imports,
    find_sensitive_keys,
    run_boundary_checks,
    validate_workflow_safety_data,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_project_local_model_boundary_checks_pass() -> None:
    results = run_boundary_checks(PROJECT_ROOT)

    assert results
    assert all(item.status == "OK" for item in results)


def test_forbidden_import_scanner_detects_http_client(
    tmp_path: Path,
) -> None:
    service_directory = tmp_path / "app/services"
    service_directory.mkdir(parents=True)
    unsafe_file = service_directory / "unsafe.py"
    unsafe_file.write_text(
        "import requests\n",
        encoding="utf-8",
    )

    findings = find_forbidden_imports(tmp_path)

    assert findings
    assert "requests" in findings[0]


def test_sensitive_key_scanner_detects_credentials() -> None:
    findings = find_sensitive_keys(
        {
            "provider": {
                "api_token": "unsafe-value",
            }
        }
    )

    assert findings == ("root.provider.api_token",)


def test_workflow_safety_rejects_live_write() -> None:
    findings = validate_workflow_safety_data(
        "shipment_draft_preview.yaml",
        {
            "non_canonical": True,
            "preview_only": True,
            "live_provider_write": True,
            "recipient": {
                "non_canonical": True,
            },
            "destination": {
                "shipment_time_snapshot": True,
            },
        },
    )

    assert any("live_provider_write must be false" in finding for finding in findings)
