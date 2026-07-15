from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DOCUMENT_PATH = PROJECT_ROOT / "docs/architecture/adapters" / "provider_registry.md"


def test_provider_registry_documentation_exists() -> None:
    assert DOCUMENT_PATH.is_file()


def test_provider_registry_documentation_records_safety() -> None:
    text = DOCUMENT_PATH.read_text(encoding="utf-8").casefold()

    concepts = (
        "providerregistry",
        "disabled by default",
        "does not auto-enable providers",
        "duplicate provider rejection",
        "capability filtering",
        "live_write_enabled = false",
        "does not expose",
        "credentials",
        "perform http or sdk calls",
        "automatically select a provider by price",
    )

    compact = "".join(text.split())

    for concept in concepts:
        assert "".join(concept.split()) in compact, concept
