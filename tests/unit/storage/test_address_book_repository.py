from app.domain import (
    AddressBookEntry,
    RecipientRef,
)
from app.storage import (
    InMemoryLogisticsRepository,
    LogisticsRepository,
)


def build_entry(
    *,
    entry_id: str,
    recipient_ref: str,
    alias: str,
    city: str,
    area_hint: str,
) -> AddressBookEntry:
    return AddressBookEntry(
        entry_id=entry_id,
        recipient=RecipientRef(
            recipient_ref=recipient_ref,
            display_name=(f"Synthetic {entry_id}"),
        ),
        aliases=(alias,),
        country_code="UA",
        city=city,
        address_line_1=(f"Synthetic {entry_id} Street"),
        area_hint=area_hint,
        search_tokens=(
            city,
            area_hint,
        ),
    )


def test_repository_saves_gets_and_lists_entries() -> None:
    repository = InMemoryLogisticsRepository()
    entry = build_entry(
        entry_id="office",
        recipient_ref="recipient_001",
        alias="офіс",
        city="Kyiv",
        area_hint="center",
    )

    assert isinstance(
        repository,
        LogisticsRepository,
    )
    assert repository.save_address_book_entry(entry) is entry
    assert repository.get_address_book_entry("office") is entry
    assert repository.list_address_book_entries() == (entry,)
    assert repository.get_recipient("recipient_001") is entry.recipient


def test_repository_searches_alias_reference_and_location() -> None:
    repository = InMemoryLogisticsRepository()
    office = build_entry(
        entry_id="office",
        recipient_ref="recipient_001",
        alias="офіс",
        city="Kyiv",
        area_hint="center",
    )
    warehouse = build_entry(
        entry_id="warehouse",
        recipient_ref="recipient_002",
        alias="склад",
        city="Kyiv",
        area_hint="left bank",
    )

    repository.save_address_book_entry(office)
    repository.save_address_book_entry(warehouse)

    assert repository.find_address_book_entries("офіс") == (office,)
    assert repository.find_address_book_entries(
        "склад",
        city_or_area_hint="left",
    ) == (warehouse,)
    assert repository.find_address_book_entries_by_recipient_ref("recipient_002") == (warehouse,)
    assert repository.find_address_book_entries("missing") == ()
