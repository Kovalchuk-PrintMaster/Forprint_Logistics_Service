from pathlib import Path

import yaml


def test_manifest_uses_canonical_logistics_module_id() -> None:
    manifest = yaml.safe_load(Path("forprint_module_manifest.yaml").read_text(encoding="utf-8"))

    assert manifest["module_id"] == "logistics_service"
    assert "delivery_request" in manifest["responsibilities"]["owns"]
    assert "order" in manifest["responsibilities"]["must_not_own"]


def test_makefile_exposes_required_bootstrap_targets() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")

    required_targets = (
        "check:",
        "test:",
        "lint:",
        "format:",
        "report-status:",
        "logistics-check:",
        "coordination-check:",
        "governance-check:",
    )

    for target in required_targets:
        assert target in makefile
