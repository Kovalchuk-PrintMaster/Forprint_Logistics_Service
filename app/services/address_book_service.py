from __future__ import annotations

from app.domain import (
    AddressBookEntry,
    AddressSnapshot,
)
from app.storage import LogisticsRepository


class AddressBookEntryNotFoundError(LookupError):
    """Raised when a local address entry is missing."""


class AddressBookService:
    """Manage local non-canonical logistics references."""

    def __init__(
        self,
        repository: LogisticsRepository,
    ) -> None:
        self._repository = repository

    def save_entry(
        self,
        entry: AddressBookEntry,
    ) -> AddressBookEntry:
        return self._repository.save_address_book_entry(entry)

    def list_entries(
        self,
    ) -> tuple[AddressBookEntry, ...]:
        return self._repository.list_address_book_entries()

    def lookup(
        self,
        query: str,
        *,
        city_or_area_hint: str | None = None,
    ) -> tuple[AddressBookEntry, ...]:
        return self._repository.find_address_book_entries(
            query,
            city_or_area_hint=(city_or_area_hint),
        )

    def find_by_recipient_ref(
        self,
        recipient_ref: str,
    ) -> tuple[AddressBookEntry, ...]:
        return self._repository.find_address_book_entries_by_recipient_ref(recipient_ref)

    def create_address_snapshot(
        self,
        entry_id: str,
    ) -> AddressSnapshot:
        entry = self._repository.get_address_book_entry(entry_id)

        if entry is None:
            raise AddressBookEntryNotFoundError(f"Address book entry was not found: {entry_id}")

        snapshot = entry.create_address_snapshot()

        if not snapshot.shipment_time_snapshot:
            raise RuntimeError("Address snapshot must remain shipment-time only")

        return snapshot
