from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MAKEFILE_PATH = PROJECT_ROOT / "Makefile"

REQUIRED_DOCUMENTS = (
    (PROJECT_ROOT / "docs/architecture/check_reporting_architecture.md"),
    (PROJECT_ROOT / "docs/development/testing/check_reporting.md"),
    (PROJECT_ROOT / "docs/operations/check_reporting_recovery.md"),
)


def test_check_report_make_targets_exist() -> None:
    text = MAKEFILE_PATH.read_text(encoding="utf-8")

    assert "check-report:" in text
    assert "check-report-full:" in text
    assert "--full" in text


def test_check_reporting_documents_exist() -> None:
    for path in REQUIRED_DOCUMENTS:
        assert path.is_file(), path
