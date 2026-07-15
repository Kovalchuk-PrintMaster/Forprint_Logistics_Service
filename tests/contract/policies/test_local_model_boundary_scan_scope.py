from pathlib import Path

from scripts.validation.check_local_model_boundaries import (
    find_forbidden_imports,
    scanned_python_paths,
)


def write_python(
    root: Path,
    relative_path: str,
    content: str,
) -> Path:
    path = root / relative_path
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        content.rstrip() + "\n",
        encoding="utf-8",
    )

    return path


def test_provider_contract_preview_is_outside_local_model_scan(
    tmp_path: Path,
) -> None:
    provider_preview = write_python(
        tmp_path,
        ("scripts/previews/preview_provider_adapter_contract.py"),
        ("from app.adapters.providers import ProviderAdapter"),
    )

    scanned = scanned_python_paths(tmp_path)
    findings = find_forbidden_imports(tmp_path)

    assert provider_preview not in scanned
    assert findings == ()


def test_local_model_preview_still_rejects_adapter_import(
    tmp_path: Path,
) -> None:
    local_preview = write_python(
        tmp_path,
        ("scripts/previews/preview_local_logistics_model.py"),
        ("from app.adapters.providers import ProviderAdapter"),
    )

    scanned = scanned_python_paths(tmp_path)
    findings = find_forbidden_imports(tmp_path)

    assert local_preview in scanned
    assert any(
        ("preview_local_logistics_model.py:1: app.adapters.providers") in finding
        for finding in findings
    )


def test_address_book_preview_remains_in_scan(
    tmp_path: Path,
) -> None:
    address_book_preview = write_python(
        tmp_path,
        ("scripts/previews/preview_test_address_book.py"),
        "from app.domain import AddressBookEntry",
    )

    scanned = scanned_python_paths(tmp_path)

    assert address_book_preview in scanned


def test_service_layer_still_rejects_adapter_import(
    tmp_path: Path,
) -> None:
    write_python(
        tmp_path,
        "app/services/unsafe_service.py",
        ("from app.adapters.providers import ProviderAdapter"),
    )

    findings = find_forbidden_imports(tmp_path)

    assert any(
        ("app/services/unsafe_service.py:1: app.adapters.providers") in finding
        for finding in findings
    )
