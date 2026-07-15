from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MAKEFILE_PATH = PROJECT_ROOT / "Makefile"


def test_provider_contract_make_targets_exist() -> None:
    text = MAKEFILE_PATH.read_text(encoding="utf-8")

    assert "provider-contract-check:" in text
    assert "provider-contract-preview:" in text


def test_main_check_runs_provider_contract_check() -> None:
    text = MAKEFILE_PATH.read_text(encoding="utf-8")

    assert "$(MAKE) provider-contract-check" in text
