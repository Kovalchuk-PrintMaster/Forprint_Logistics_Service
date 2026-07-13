import pytest

from app.domain import (
    AddressBookEntry,
    RecipientRef,
)


def build_entry(
    **overrides: object,
) -> AddressBookEntry:
    values: dict[str, object] = {
        "entry_id": "address_kyiv_office",
        "recipient": RecipientRef(
            recipient_ref=("test_recipient_kyiv"),
            display_name=("Synthetic Kyiv Recipient"),
        ),
        "aliases": (
            " Офіс ",
            "офіс",
            "Київський отримувач",
        ),
        "country_code": "ua",
        "city": "Kyiv",
        "address_line_1": ("Synthetic Street 1"),
        "area_hint": "лівий берег",
        "search_tokens": (
            " тестова адреса ",
            "офіс",
        ),
    }
    values.update(overrides)
    return AddressBookEntry(**values)


def test_entry_is_non_canonical_and_normalizes_lookup_values() -> None:
    entry = build_entry()

    assert entry.non_canonical is True
    assert entry.logistics_reference_only is True
    assert entry.country_code == "UA"
    assert entry.aliases == (
        "офіс",
        "київський отримувач",
    )
    assert entry.search_tokens == (
        "тестова адреса",
        "офіс",
    )


def test_entry_matches_alias_name_token_and_city_hint() -> None:
    entry = build_entry()

    assert entry.matches("офіс")
    assert entry.matches("synthetic kyiv")
    assert entry.matches(
        "тестова адреса",
        city_or_area_hint="лівий",
    )
    assert not entry.matches(
        "офіс",
        city_or_area_hint="odesa",
    )


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("non_canonical", False),
        (
            "logistics_reference_only",
            False,
        ),
    ),
)
def test_entry_rejects_canonical_ownership_flags(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(ValueError):
        build_entry(**{field_name: value})
