from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_GREEN = "\033[32m"
ANSI_YELLOW = "\033[33m"
ANSI_RED = "\033[31m"

CHECK_COMMANDS: tuple[
    tuple[str, tuple[str, ...], str],
    ...,
] = (
    (
        "Python compile",
        ("make", "compile"),
        "All Python source files compile.",
    ),
    (
        "Ruff lint",
        ("make", "lint"),
        "No Ruff lint errors.",
    ),
    (
        "Ruff format",
        ("make", "format-check"),
        "All Python files are formatted.",
    ),
    (
        "Pytest",
        ("make", "test"),
        "All tests pass.",
    ),
    (
        "Project policies",
        ("make", "project-policy-check"),
        "Module boundaries and local policies are valid.",
    ),
    (
        "Local model examples",
        ("make", "local-model-examples-check"),
        "Preview workflow examples are safe and valid.",
    ),
    (
        "Coordination metadata",
        ("make", "coordination-check"),
        "Coordination metadata is valid.",
    ),
)


@dataclass(frozen=True, slots=True)
class CheckResult:
    name: str
    expected: str
    status: str
    duration_seconds: float
    details: str
    command: list[str]


def normalize_status(status: str) -> str:
    normalized = status.strip().upper()

    if normalized in {"FAILED", "FAIL", "ERROR"}:
        return "FAILED"

    if normalized in {"WARN", "WARNING"}:
        return "WARN"

    if normalized == "SKIPPED":
        return "SKIPPED"

    if normalized == "OK":
        return "OK"

    return "WARN"


def overall_status(
    results: Sequence[CheckResult],
) -> str:
    statuses = {normalize_status(result.status) for result in results}

    if "FAILED" in statuses:
        return "FAILED"

    if statuses.intersection({"WARN", "SKIPPED"}):
        return "WARN"

    return "OK"


def plain_status_text(status: str) -> str:
    normalized = normalize_status(status)

    if normalized == "OK":
        return "✓ OK"

    if normalized == "FAILED":
        return "✗ FAILED"

    if normalized == "SKIPPED":
        return "! SKIPPED"

    return "! WARN"


def markdown_status_text(status: str) -> str:
    normalized = normalize_status(status)

    if normalized == "OK":
        return "✅ OK"

    if normalized == "FAILED":
        return "❌ FAILED"

    if normalized == "SKIPPED":
        return "⚠️ SKIPPED"

    return "⚠️ WARN"


def status_color(status: str) -> str:
    normalized = normalize_status(status)

    if normalized == "OK":
        return ANSI_GREEN

    if normalized == "FAILED":
        return ANSI_RED

    return ANSI_YELLOW


def color_enabled() -> bool:
    if "NO_COLOR" in os.environ:
        return False

    force_color = (
        os.environ.get(
            "FORCE_COLOR",
            "",
        )
        .strip()
        .lower()
    )

    if force_color in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return True

    if os.environ.get("TERM") == "dumb":
        return False

    return sys.stdout.isatty()


def colorize(
    value: str,
    color: str,
    use_color: bool,
) -> str:
    if not use_color:
        return value

    return f"{color}{value}{ANSI_RESET}"


def run_command(
    name: str,
    command: Sequence[str],
    expected: str,
    project_root: Path,
) -> CheckResult:
    started = time.monotonic()
    environment = os.environ.copy()
    environment["NO_COLOR"] = "1"

    completed = subprocess.run(
        list(command),
        cwd=project_root,
        check=False,
        text=True,
        capture_output=True,
        env=environment,
    )

    duration = time.monotonic() - started

    output = "\n".join(
        part.strip()
        for part in (
            completed.stdout,
            completed.stderr,
        )
        if part.strip()
    )

    return CheckResult(
        name=name,
        expected=expected,
        status=("OK" if completed.returncode == 0 else "FAILED"),
        duration_seconds=round(duration, 4),
        details=output or "No command output.",
        command=list(command),
    )


def build_json_report(
    results: Sequence[CheckResult],
    generated_at: str,
) -> dict[str, Any]:
    return {
        "module_id": "logistics_service",
        "generated_at": generated_at,
        "overall_status": overall_status(results),
        "checks": [asdict(result) for result in results],
    }


def build_markdown_report(
    results: Sequence[CheckResult],
    generated_at: str,
) -> str:
    report_status = overall_status(results)

    rows = [
        "| Check | Expected | Status | Time |",
        "|---|---|---:|---:|",
    ]

    for result in results:
        rows.append(
            f"| {result.name} | {result.expected} | "
            f"{markdown_status_text(result.status)} | "
            f"{result.duration_seconds:.4f}s |"
        )

    details: list[str] = []

    for result in results:
        details.extend(
            [
                f"## {result.name}",
                "",
                (f"- Status: `{normalize_status(result.status)}`"),
                (f"- Command: `{' '.join(result.command)}`"),
                "",
                "```text",
                result.details,
                "```",
                "",
            ]
        )

    return "\n".join(
        [
            ("# ForPrint Logistics Service — check report"),
            "",
            f"- Generated at: `{generated_at}`",
            f"- Overall status: `{report_status}`",
            "",
            *rows,
            "",
            *details,
        ]
    )


def _format_cell(
    value: str,
    width: int,
    alignment: str,
) -> str:
    if alignment == "right":
        padded = value.rjust(width)
    elif alignment == "center":
        padded = value.center(width)
    else:
        padded = value.ljust(width)

    return f" {padded} "


def _border(
    left: str,
    middle: str,
    right: str,
    widths: Sequence[int],
) -> str:
    segments = ["─" * (width + 2) for width in widths]

    return left + middle.join(segments) + right


def build_console_summary(
    results: Sequence[CheckResult],
    *,
    use_color: bool,
) -> str:
    headers = (
        "#",
        "Check",
        "Expected",
        "Result",
        "Time",
    )
    alignments = (
        "right",
        "left",
        "left",
        "center",
        "right",
    )

    rows = [
        (
            str(index),
            result.name,
            result.expected,
            plain_status_text(result.status),
            f"{result.duration_seconds:.4f}s",
        )
        for index, result in enumerate(
            results,
            start=1,
        )
    ]

    widths = [
        max(
            len(headers[column]),
            *(len(row[column]) for row in rows),
        )
        for column in range(len(headers))
    ]

    lines: list[str] = []

    title = "ForPrint Logistics Service — check report"
    lines.append(
        colorize(
            title,
            ANSI_BOLD,
            use_color,
        )
    )
    lines.append("")

    lines.append(
        _border(
            "┌",
            "┬",
            "┐",
            widths,
        )
    )

    header_cells = [
        _format_cell(
            value,
            widths[index],
            alignments[index],
        )
        for index, value in enumerate(headers)
    ]

    if use_color:
        header_cells = [
            colorize(
                cell,
                ANSI_BOLD,
                True,
            )
            for cell in header_cells
        ]

    lines.append("│" + "│".join(header_cells) + "│")

    lines.append(
        _border(
            "├",
            "┼",
            "┤",
            widths,
        )
    )

    for index, row in enumerate(rows):
        result = results[index]
        cells: list[str] = []

        for column, value in enumerate(row):
            cell = _format_cell(
                value,
                widths[column],
                alignments[column],
            )

            if column == 3:
                cell = colorize(
                    cell,
                    status_color(result.status),
                    use_color,
                )

            cells.append(cell)

        lines.append("│" + "│".join(cells) + "│")

    lines.append(
        _border(
            "└",
            "┴",
            "┘",
            widths,
        )
    )

    normalized_statuses = [normalize_status(result.status) for result in results]

    passed_count = normalized_statuses.count("OK")
    warning_count = sum(status in {"WARN", "SKIPPED"} for status in normalized_statuses)
    failed_count = normalized_statuses.count("FAILED")

    report_status = overall_status(results)

    lines.extend(
        [
            "",
            (
                f"Checks: {len(results)} total"
                f" | {passed_count} passed"
                f" | {warning_count} warning"
                f" | {failed_count} failed"
            ),
            (
                "Overall status: "
                + colorize(
                    plain_status_text(report_status),
                    status_color(report_status),
                    use_color,
                )
            ),
        ]
    )

    return "\n".join(lines)


def _print_console_summary(
    results: Sequence[CheckResult],
) -> None:
    print(
        build_console_summary(
            results,
            use_color=color_enabled(),
        )
    )


def run_checks(
    project_root: Path,
) -> list[CheckResult]:
    return [
        run_command(
            name,
            command,
            expected,
            project_root,
        )
        for name, command, expected in CHECK_COMMANDS
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=("Run Logistics Service checks and generate reports.")
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
    )
    parser.add_argument(
        "--list-checks",
        action="store_true",
    )
    args = parser.parse_args()

    if args.list_checks:
        for name, command, _expected in CHECK_COMMANDS:
            print(f"{name}: {' '.join(command)}")

        return 0

    project_root = args.project_root.resolve()
    reports_dir = project_root / "reports"
    reports_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    generated_at = datetime.now(UTC).isoformat()
    results = run_checks(project_root)

    json_report = build_json_report(
        results,
        generated_at,
    )
    markdown_report = build_markdown_report(
        results,
        generated_at,
    )

    json_path = reports_dir / "logistics_service_check_report.json"
    markdown_path = reports_dir / "logistics_service_check_report.md"

    json_path.write_text(
        json.dumps(
            json_report,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    markdown_path.write_text(
        markdown_report.rstrip() + "\n",
        encoding="utf-8",
    )

    _print_console_summary(results)

    print("")
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {markdown_path}")

    return 1 if json_report["overall_status"] == "FAILED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
