import pytest

from app.domain import (
    AddressBookEntry,
    RecipientRef,
)
from app.services import (
    AddressBookEntryNotFoundError,
    AddressBookService,
)
from app.storage import (
    InMemoryLogisticsRepository,
)


def build_service() -> tuple[
    AddressBookService,
    AddressBookEntry,
]:
    repository = InMemoryLogisticsRepository()
    service = AddressBookService(repository)
    entry = AddressBookEntry(
        entry_id="test_office",
        recipient=RecipientRef(
            recipient_ref=("test_recipient_office"),
            display_name=("Synthetic Office Recipient"),
        ),
        aliases=(
            "офіс",
            "тестовий отримувач",
        ),
        country_code="UA",
        city="Kyiv",
        address_line_1=("Synthetic Office Street 10"),
        postal_code="00000",
        area_hint="center",
        search_tokens=("київський отримувач",),
    )
    service.save_entry(entry)

    return service, entry


def test_service_lookup_and_recipient_reference() -> None:
    service, entry = build_service()

    assert service.lookup("офіс") == (entry,)
    assert service.find_by_recipient_ref("test_recipient_office") == (entry,)
    assert service.list_entries() == (entry,)


def test_service_creates_shipment_time_snapshot() -> None:
    service, _ = build_service()

    snapshot = service.create_address_snapshot("test_office")

    assert snapshot.shipment_time_snapshot is True
    assert snapshot.country_code == "UA"
    assert snapshot.city == "Kyiv"
    assert snapshot.address_line_1 == ("Synthetic Office Street 10")


def test_service_rejects_missing_entry() -> None:
    service, _ = build_service()

    with pytest.raises(AddressBookEntryNotFoundError):
        service.create_address_snapshot("missing")
