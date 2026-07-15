from scripts.diagnostics.run_logistics_checks import (
    CHECK_COMMANDS,
)


def test_provider_contract_check_is_visible() -> None:
    checks = {name: command for name, command, _expected in CHECK_COMMANDS}

    assert checks["Provider contract"] == (
        "make",
        "provider-contract-check",
    )
