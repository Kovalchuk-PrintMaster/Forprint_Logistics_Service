from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = PROJECT_ROOT / "examples/fixtures/address_book/test_address_book.yaml"


def load_fixture() -> dict[str, object]:
    data = yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_address_book_fixture_exists() -> None:
    assert FIXTURE_PATH.is_file()


def test_fixture_is_synthetic_and_safe() -> None:
    data = load_fixture()

    assert data["non_canonical"] is True
    assert data["preview_only"] is True
    assert data["live_provider_write"] is False
    assert data["synthetic_data"] is True
    assert data["real_customer_data"] is False


def test_fixture_contains_required_entry_kinds() -> None:
    data = load_fixture()
    entries = data["entries"]

    assert isinstance(entries, list)
    assert len(entries) == 3

    kinds = {entry["entry_kind"] for entry in entries}

    assert kinds == {
        "kyiv_local",
        "warehouse",
        "office",
    }


def test_fixture_contains_no_private_recipient_data() -> None:
    data = load_fixture()

    for entry in data["entries"]:
        assert entry["synthetic_data"] is True
        assert entry["real_customer_data"] is False
        assert entry["non_canonical"] is True

        recipient = entry["recipient"]

        assert recipient["recipient_ref"].startswith("test_recipient_")
        assert recipient["display_name"].startswith("Synthetic ")
        assert recipient["phone"] is None
        assert recipient["non_canonical"] is True

        assert entry["aliases"]
        assert entry["address"]["address_line_1"].startswith("Synthetic ")
