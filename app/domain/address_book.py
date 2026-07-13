from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.recipients import (
    AddressSnapshot,
    RecipientRef,
)


def normalize_lookup_token(value: str) -> str:
    """Normalize safe local lookup text."""

    return " ".join(value.strip().casefold().split())


def _normalized_unique(
    values: tuple[str, ...],
    *,
    field_name: str,
) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()

    for value in values:
        token = normalize_lookup_token(value)

        if not token:
            raise ValueError(f"{field_name} must not contain empty values")

        if token in seen:
            continue

        seen.add(token)
        normalized.append(token)

    return tuple(normalized)


@dataclass(frozen=True, slots=True)
class AddressBookEntry:
    """Non-canonical local logistics address book entry."""

    entry_id: str
    recipient: RecipientRef
    aliases: tuple[str, ...]
    country_code: str
    city: str
    address_line_1: str
    postal_code: str | None = None
    address_line_2: str | None = None
    provider_location_ref: str | None = None
    area_hint: str | None = None
    search_tokens: tuple[str, ...] = field(default_factory=tuple)
    source_system: str = "local_fixture"
    non_canonical: bool = True
    logistics_reference_only: bool = True

    def __post_init__(self) -> None:
        entry_id = self.entry_id.strip()
        country_code = self.country_code.strip().upper()
        city = self.city.strip()
        address_line_1 = self.address_line_1.strip()
        source_system = self.source_system.strip()

        if not entry_id:
            raise ValueError("entry_id must not be empty")

        if not self.recipient.non_canonical:
            raise ValueError("Address book recipient must remain non-canonical")

        if not self.aliases:
            raise ValueError("Address book entry must contain at least one alias")

        if len(country_code) != 2:
            raise ValueError("country_code must contain a two-letter country code")

        if not city:
            raise ValueError("city must not be empty")

        if not address_line_1:
            raise ValueError("address_line_1 must not be empty")

        if not source_system:
            raise ValueError("source_system must not be empty")

        if not self.non_canonical:
            raise ValueError("Address book entries must remain non-canonical")

        if not self.logistics_reference_only:
            raise ValueError("Address book entries must remain logistics references only")

        object.__setattr__(
            self,
            "entry_id",
            entry_id,
        )
        object.__setattr__(
            self,
            "country_code",
            country_code,
        )
        object.__setattr__(
            self,
            "city",
            city,
        )
        object.__setattr__(
            self,
            "address_line_1",
            address_line_1,
        )
        object.__setattr__(
            self,
            "source_system",
            source_system,
        )
        object.__setattr__(
            self,
            "aliases",
            _normalized_unique(
                self.aliases,
                field_name="aliases",
            ),
        )
        object.__setattr__(
            self,
            "search_tokens",
            _normalized_unique(
                self.search_tokens,
                field_name="search_tokens",
            ),
        )

    def matches(
        self,
        query: str,
        *,
        city_or_area_hint: str | None = None,
    ) -> bool:
        """Match a safe local lookup query."""

        query_token = normalize_lookup_token(query)

        if not query_token:
            return False

        candidates = (
            normalize_lookup_token(self.entry_id),
            normalize_lookup_token(self.recipient.recipient_ref),
            normalize_lookup_token(self.recipient.display_name),
            *self.aliases,
            *self.search_tokens,
        )

        query_matches = any(
            query_token == candidate or query_token in candidate
            for candidate in candidates
            if candidate
        )

        if not query_matches:
            return False

        if city_or_area_hint is None:
            return True

        hint = normalize_lookup_token(city_or_area_hint)

        if not hint:
            return True

        location_candidates = (
            normalize_lookup_token(self.city),
            normalize_lookup_token(self.area_hint or ""),
            *self.search_tokens,
        )

        return any(
            hint == candidate or hint in candidate for candidate in location_candidates if candidate
        )

    def create_address_snapshot(
        self,
    ) -> AddressSnapshot:
        """Create a shipment-time address snapshot."""

        return AddressSnapshot(
            country_code=self.country_code,
            city=self.city,
            address_line_1=(self.address_line_1),
            postal_code=self.postal_code,
            address_line_2=(self.address_line_2),
            provider_location_ref=(self.provider_location_ref),
            shipment_time_snapshot=True,
        )
