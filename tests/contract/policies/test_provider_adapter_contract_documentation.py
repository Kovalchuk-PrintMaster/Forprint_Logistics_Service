from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = PROJECT_ROOT / "docs/architecture/provider_adapter_contract.md"
POLICY_PATH = PROJECT_ROOT / "docs/architecture/adapters" / "provider_adapter_policy.md"


def test_provider_contract_documents_exist() -> None:
    assert CONTRACT_PATH.is_file()
    assert POLICY_PATH.is_file()


def test_provider_contract_covers_typed_boundary() -> None:
    text = CONTRACT_PATH.read_text(encoding="utf-8").casefold()
    compact = "".join(text.split())

    concepts = (
        "provideradapter",
        "validate_recipient",
        "validate_address",
        "build_shipment_payload_preview",
        "trackinglookupresult",
        "deliveryquotelookupresult",
        "dryrunpayloadenvelope",
        "providererrorcode",
        "live_write=false",
        "provider_call_performed=false",
        "unsupported_capability",
        "create_shipment()isfinal",
    )

    for concept in concepts:
        assert "".join(concept.split()) in compact, concept


def test_provider_policy_records_forbidden_writes() -> None:
    text = POLICY_PATH.read_text(encoding="utf-8").casefold()

    concepts = (
        "create a ttn",
        "submit a shipment",
        "book a courier",
        "book a taxi",
        "real production credentials",
        "final customer price",
        "live_write = false",
    )

    for concept in concepts:
        assert concept in text, concept
