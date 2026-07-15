from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DOCUMENT_PATH = PROJECT_ROOT / "docs/architecture/provider_adapter_contract.md"


def test_provider_contract_documentation_exists() -> None:
    assert DOCUMENT_PATH.is_file()


def test_provider_contract_documentation_covers_boundaries() -> None:
    text = DOCUMENT_PATH.read_text(encoding="utf-8").casefold()

    required_concepts = (
        "providercapability",
        "provideroperation",
        "dryrunpayloadenvelope",
        "providererrorcode",
        "live_write = false",
        "provider_call_performed = false",
        "real credentials",
        "provider-side writes",
    )

    compact = "".join(text.split())

    for concept in required_concepts:
        assert "".join(concept.split()) in compact, concept
