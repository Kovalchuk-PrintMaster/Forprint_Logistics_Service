from scripts.diagnostics.run_logistics_checks import (
    CheckResult,
    build_json_report,
    build_markdown_report,
)


def build_results() -> list[CheckResult]:
    return [
        CheckResult(
            name="Example check",
            expected="Example passes.",
            status="OK",
            duration_seconds=0.1,
            details="Everything is fine.",
            command=["make", "example"],
        )
    ]


def test_json_check_report_is_machine_readable() -> None:
    report = build_json_report(
        build_results(),
        "2026-07-11T20:00:00+03:00",
    )

    assert report["module_id"] == "logistics_service"
    assert report["overall_status"] == "OK"
    assert report["checks"][0]["name"] == "Example check"


def test_markdown_check_report_is_human_readable() -> None:
    report = build_markdown_report(
        build_results(),
        "2026-07-11T20:00:00+03:00",
    )

    assert "# ForPrint Logistics Service — check report" in report
    assert "| Example check |" in report
    assert "Overall status: `OK`" in report
