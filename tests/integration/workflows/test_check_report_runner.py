import sys

from scripts.diagnostics.run_logistics_checks import (
    CheckResult,
    build_console_summary,
    build_full_console_output,
    build_json_report,
    build_markdown_report,
    run_command,
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
            diagnostics_path=("reports/diagnostics/example_check.log"),
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
        "2026-07-15T12:00:00+00:00",
    )

    assert report["module_id"] == ("logistics_service")
    assert report["overall_status"] == "OK"
    assert report["checks"][0]["name"] == ("Example check")
    assert report["diagnostics_directory"] == ("reports/diagnostics")


def test_markdown_check_report_is_human_readable() -> None:
    report = build_markdown_report(
        build_results(),
        "2026-07-15T12:00:00+00:00",
    )

    assert ("# ForPrint Logistics Service — check report") in report
    assert "| Example check |" in report
    assert "✅ OK" in report
    assert "Overall status: `OK`" in report
    assert ("reports/diagnostics/example_check.log") in report
    assert "Everything is fine." not in report


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
    assert "Passed." not in report
    assert "\033[" not in report


def test_console_summary_supports_ansi_colors() -> None:
    report = build_console_summary(
        build_results(),
        use_color=True,
    )

    assert "\033[36m" in report
    assert "\033[32m" in report
    assert "\033[0m" in report


def test_full_output_contains_command_details() -> None:
    report = build_full_console_output(
        build_results(),
        use_color=False,
    )

    assert "Everything is fine." in report
    assert "Command: make example" in report
    assert ("reports/diagnostics/example_check.log") in report


def test_run_command_writes_diagnostic_log(
    tmp_path,
) -> None:
    diagnostics_dir = tmp_path / "reports" / "diagnostics"

    result = run_command(
        "Example command",
        (
            sys.executable,
            "-c",
            "print('diagnostic output')",
        ),
        "Command succeeds.",
        tmp_path,
        diagnostics_dir,
    )

    assert result.status == "OK"
    assert result.diagnostics_path == ("reports/diagnostics/example_command.log")

    log_path = tmp_path / result.diagnostics_path

    assert log_path.is_file()
    assert "diagnostic output" in (log_path.read_text(encoding="utf-8"))
