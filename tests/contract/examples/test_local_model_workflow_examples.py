from pathlib import Path

import yaml

from scripts.previews.preview_local_logistics_model import (
    EXAMPLE_FILENAMES,
    build_local_model_preview,
    load_workflow_examples,
    render_preview,
)

EXAMPLES_ROOT = Path("examples/workflows")


def test_examples_have_required_safety_flags() -> None:
    examples = load_workflow_examples(EXAMPLES_ROOT)

    assert set(examples) == set(EXAMPLE_FILENAMES)

    for data in examples.values():
        assert data["non_canonical"] is True
        assert data["preview_only"] is True
        assert data["live_provider_write"] is False


def test_examples_are_valid_yaml_mappings() -> None:
    for filename in EXAMPLE_FILENAMES:
        path = EXAMPLES_ROOT / filename
        data = yaml.safe_load(path.read_text(encoding="utf-8"))

        assert isinstance(data, dict)
        assert data["schema_version"]


def test_examples_build_complete_local_flow() -> None:
    preview = build_local_model_preview(EXAMPLES_ROOT)

    assert preview.draft.preview_only is True
    assert preview.draft.live_provider_write is False
    assert preview.tracking_request.local_only is True
    assert preview.tracking_request.provider_call_performed is False
    assert len(preview.tracking_events) == 3
    assert preview.notification.delivery_performed is False

    assert len(preview.repository.list_providers()) == 1
    assert len(preview.repository.list_recipients()) == 1
    assert len(preview.repository.list_shipment_drafts()) == 1
    assert len(preview.repository.list_tracking_requests()) == 1
    assert len(preview.repository.list_tracking_events()) == 3
    assert len(preview.repository.list_notification_events()) == 1


def test_preview_is_human_readable() -> None:
    preview = build_local_model_preview(EXAMPLES_ROOT)
    output = render_preview(preview)

    assert "Nova Poshta / local example provider" in output
    assert "non-canonical" in output
    assert "shipment-time snapshot" in output
    assert "preview-only" in output
    assert "local-only" in output
    assert "Telegram Bot / CRM / Website" in output
    assert "Live provider write" in output
    assert "DISABLED" in output
    assert "No external provider call was performed." in output
