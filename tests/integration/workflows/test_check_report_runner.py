from scripts.diagnostics.run_logistics_checks import (
    CheckResult,
    build_console_summary,
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


def build_mixed_results() -> list[CheckResult]:
    return [
        CheckResult(
            name="Passing check",
            expected="Passes cleanly.",
            status="OK",
            duration_seconds=0.1,
            details="Passed.",
            command=["make", "pass"],
        ),
        CheckResult(
            name="Warning check",
            expected="May report a warning.",
            status="WARN",
            duration_seconds=0.2,
            details="Warning.",
            command=["make", "warn"],
        ),
        CheckResult(
            name="Failed check",
            expected="Must pass.",
            status="FAILED",
            duration_seconds=0.3,
            details="Failed.",
            command=["make", "fail"],
        ),
    ]


def test_json_check_report_is_machine_readable() -> None:
    report = build_json_report(
        build_results(),
        "2026-07-11T20:00:00+03:00",
    )

    assert report["module_id"] == "logistics_service"
    assert report["overall_status"] == "OK"
    assert report["checks"][0]["name"] == ("Example check")


def test_markdown_check_report_is_human_readable() -> None:
    report = build_markdown_report(
        build_results(),
        "2026-07-11T20:00:00+03:00",
    )

    assert "# ForPrint Logistics Service — check report" in report
    assert "| Example check |" in report
    assert "✅ OK" in report
    assert "Overall status: `OK`" in report


def test_console_summary_contains_visual_table() -> None:
    report = build_console_summary(
        build_mixed_results(),
        use_color=False,
    )

    assert "┌" in report
    assert "┬" in report
    assert "└" in report
    assert "Passing check" in report
    assert "✓ OK" in report
    assert "! WARN" in report
    assert "✗ FAILED" in report
    assert "3 total" in report
    assert "1 passed" in report
    assert "1 warning" in report
    assert "1 failed" in report
    assert "Overall status: ✗ FAILED" in report
    assert "\033[" not in report


def test_console_summary_supports_ansi_colors() -> None:
    report = build_console_summary(
        build_results(),
        use_color=True,
    )

    assert "\033[1m" in report
    assert "\033[32m" in report
    assert "\033[0m" in report
