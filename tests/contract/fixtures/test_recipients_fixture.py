from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = PROJECT_ROOT / "examples" / "fixtures" / "recipients" / "test_recipients.yaml"


def test_recipient_fixture_exists() -> None:
    assert FIXTURE_PATH.is_file()


def test_recipient_fixture_is_safe_and_non_canonical() -> None:
    data = yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert data["non_canonical"] is True
    assert data["purpose"] == "local logistics testing only"
    assert data["ownership"]["canonical_client_owner_claimed"] is False
    assert data["ownership"]["canonical_address_owner_claimed"] is False

    recipients = data["recipients"]

    assert recipients
    assert all(recipient["non_canonical"] is True for recipient in recipients)
    assert all(recipient["source_system"] == "local_fixture" for recipient in recipients)


def test_recipient_fixture_contains_only_test_references() -> None:
    data = yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))

    for recipient in data["recipients"]:
        assert recipient["recipient_ref"].startswith("test_recipient_")
        assert recipient["phone"].startswith("+380000000")
