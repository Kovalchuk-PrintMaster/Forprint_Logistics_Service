from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RecipientRef:
    """Non-canonical logistics reference to a recipient."""

    recipient_ref: str
    display_name: str
    phone: str | None = None
    source_system: str = "local_fixture"
    non_canonical: bool = True

    def __post_init__(self) -> None:
        if not self.recipient_ref.strip():
            raise ValueError("recipient_ref must not be empty")

        if not self.display_name.strip():
            raise ValueError("display_name must not be empty")

        if not self.non_canonical:
            raise ValueError("Logistics recipient references must remain non-canonical")


@dataclass(frozen=True, slots=True)
class AddressSnapshot:
    """Shipment-time snapshot, not canonical address ownership."""

    country_code: str
    city: str
    address_line_1: str
    postal_code: str | None = None
    address_line_2: str | None = None
    provider_location_ref: str | None = None
    shipment_time_snapshot: bool = True

    def __post_init__(self) -> None:
        if len(self.country_code.strip()) != 2:
            raise ValueError("country_code must contain a two-letter country code")

        if not self.city.strip():
            raise ValueError("city must not be empty")

        if not self.address_line_1.strip():
            raise ValueError("address_line_1 must not be empty")

        if not self.shipment_time_snapshot:
            raise ValueError("Logistics addresses must remain shipment-time snapshots")
