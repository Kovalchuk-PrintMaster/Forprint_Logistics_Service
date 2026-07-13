from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.validation.check_local_model_boundaries import (
    run_boundary_checks,
)
from scripts.validation.check_project_policies import (
    LOCAL_OWNER_ADDRESS_BOOK_PATH,
    run_policy_checks,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_address_book_boundary_documentation_is_complete() -> None:
    boundary = (
        (PROJECT_ROOT / "docs/architecture/boundaries/test_address_book_boundary.md")
        .read_text(encoding="utf-8")
        .lower()
    )

    test_policy = (
        (PROJECT_ROOT / "docs/development/testing/local_test_data_policy.md")
        .read_text(encoding="utf-8")
        .lower()
    )

    assert "not a canonical client database" in boundary
    assert "aliases are not client identity" in boundary
    assert "shipment-time" in boundary
    assert "telegram bot" in boundary
    assert "crm" in boundary
    assert "website" in boundary
    assert LOCAL_OWNER_ADDRESS_BOOK_PATH in boundary
    assert LOCAL_OWNER_ADDRESS_BOOK_PATH in test_policy


def test_owner_address_book_path_is_ignored_and_untracked() -> None:
    ignored = subprocess.run(
        [
            "git",
            "check-ignore",
            "--quiet",
            "--",
            LOCAL_OWNER_ADDRESS_BOOK_PATH,
        ],
        cwd=PROJECT_ROOT,
        check=False,
    )
    tracked = subprocess.run(
        [
            "git",
            "ls-files",
            "--error-unmatch",
            "--",
            LOCAL_OWNER_ADDRESS_BOOK_PATH,
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert ignored.returncode == 0
    assert tracked.returncode != 0


def test_local_model_boundary_checks_include_address_book() -> None:
    results = run_boundary_checks(PROJECT_ROOT)
    by_name = {result.name: result for result in results}

    assert by_name["Test address book boundary"].status == "OK"


def test_project_policy_checks_include_private_data_policy() -> None:
    results = run_policy_checks(PROJECT_ROOT)
    by_name = {result.name: result for result in results}

    assert by_name["Synthetic address book fixture"].status == "OK"
    assert by_name["Local owner address book"].status == "OK"
