from scripts.diagnostics.run_logistics_checks import (
    CHECK_COMMANDS,
)


def test_address_book_check_is_visible_in_report() -> None:
    checks = {name: command for name, command, _expected in CHECK_COMMANDS}

    assert checks["Test address book"] == (
        "make",
        "test-address-book-check",
    )
