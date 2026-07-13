import yaml

from scripts.previews.preview_test_address_book import (
    DEFAULT_FIXTURE_PATH,
    DEFAULT_WORKFLOW_PATH,
    build_test_address_book_preview,
    render_preview,
)


def test_address_book_workflow_flags() -> None:
    data = yaml.safe_load(DEFAULT_WORKFLOW_PATH.read_text(encoding="utf-8"))

    assert data["non_canonical"] is True
    assert data["preview_only"] is True
    assert data["live_provider_write"] is False
    assert data["synthetic_data"] is True
    assert data["real_customer_data"] is False


def test_workflow_builds_safe_preview() -> None:
    preview = build_test_address_book_preview(
        DEFAULT_FIXTURE_PATH,
        DEFAULT_WORKFLOW_PATH,
    )

    assert len(preview.entries) == 3
    assert preview.selected_entry.entry_id == "test_address_office"
    assert preview.selected_entry.non_canonical is True
    assert preview.snapshot.shipment_time_snapshot is True
    assert preview.draft.preview_only is True
    assert preview.draft.live_provider_write is False
    assert preview.provider_call_performed is False

    assert len(preview.repository.list_address_book_entries()) == 3
    assert len(preview.repository.list_shipment_drafts()) == 1


def test_workflow_preview_is_human_readable() -> None:
    preview = build_test_address_book_preview()
    output = render_preview(preview)

    assert "Test address book: local synthetic entries" in output
    assert "Entry count: 3" in output
    assert "Lookup by alias: OK" in output
    assert "Recipient reference: non-canonical" in output
    assert "Address snapshot: shipment-time snapshot" in output
    assert "created without provider API call" in output
    assert "Live provider write: disabled" in output
