from pathlib import Path

ARCHITECTURE_PATH = Path("docs/architecture/tracking_event_contract.md")
NOTIFICATION_BOUNDARY_PATH = Path("docs/architecture/boundaries/notification_handoff_boundary.md")
RUNBOOK_PATH = Path("docs/operations/tracking_events_runbook.md")
RECOVERY_PATH = Path("docs/operations/tracking_events_recovery.md")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_tracking_event_contract_documentation_is_complete() -> None:
    text = read(ARCHITECTURE_PATH)

    for required in (
        "tracking_event_v0_1",
        "shipment_created",
        "tracking_updated",
        "arrived",
        "delivered",
        "failed",
        "needs_attention",
        "accepted",
        "duplicate",
        "out_of_order",
        "invalid_transition",
        "terminal_state",
        "correlation_id",
        "causation_id",
        "idempotency",
        "app/domain/tracking.py",
        "app/services/tracking_contract_service.py",
        "examples/fixtures/tracking_events/synthetic_tracking_events.yaml",
    ):
        assert required in text


def test_notification_boundary_remains_channel_neutral() -> None:
    text = read(NOTIFICATION_BOUNDARY_PATH)

    for required in (
        "logistics_notification_projection_v0_1",
        "notification_key",
        "notification_type",
        "event_version",
        "recipient_reference",
        "safe rendering facts",
        "priority",
        "correlation ID",
        "idempotency",
        "preview_only = true",
        "telegram_api_call_performed = false",
        "cross_repository_write = false",
    ):
        assert required in text

    for forbidden_ownership in (
        "Logistics Service owns final Telegram wording",
        "Logistics Service owns chat state",
        "Logistics Service owns inline buttons",
    ):
        assert forbidden_ownership not in text


def test_runbook_documents_make_first_workflow() -> None:
    text = read(RUNBOOK_PATH)

    for required in (
        "make tracking-events-check",
        "make tracking-events-preview",
        "make check-report",
        "make check-report-full",
        "make governance-check",
        "make module-validate",
        "reports/previews/tracking_events_contract_preview.json",
        "make report-clean",
        "eleven checks",
    ):
        assert required in text


def test_recovery_guide_records_checkpoints_and_safe_restore() -> None:
    text = read(RECOVERY_PATH)

    for required in (
        "4812047963427043d616871075ac807a35e51aff",
        "344732b393e1b18e30b673f1777c27bd1ed57784",
        "61ca42ba95a62ce3a91335e273c4edf2d5d23754",
        "91d53512e2af40fcc800c44d331ff604c50cc813",
        "git restore --source",
        "make tracking-events-check",
        "make check-report-full",
        "preview_only = true",
        "telegram_api_call_performed = false",
        "cross_repository_write = false",
    ):
        assert required in text

    assert "git reset --hard" in text
    assert "Do not use `git reset --hard`" in text
