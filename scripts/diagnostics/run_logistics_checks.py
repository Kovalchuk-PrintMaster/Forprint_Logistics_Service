from __future__ import annotations

import argparse
import json
import os
import re
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
ANSI_CYAN = "\033[36m"

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
        "Local model boundaries",
        ("make", "local-model-boundary-check"),
        "Local ownership and dependency boundaries are enforced.",
    ),
    (
        "Test address book",
        ("make", "test-address-book-check"),
        "Synthetic address book fixtures and preview are safe.",
    ),
    (
        "Provider contract",
        ("make", "provider-contract-check"),
        "Provider adapters remain typed, preview-only and non-live.",
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
    diagnostics_path: str | None = None


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


def diagnostics_slug(value: str) -> str:
    slug = re.sub(
        r"[^a-z0-9]+",
        "_",
        value.strip().casefold(),
    ).strip("_")

    return slug or "check"


def run_command(
    name: str,
    command: Sequence[str],
    expected: str,
    project_root: Path,
    diagnostics_dir: Path | None = None,
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

    output = (
        "\n".join(
            part.strip()
            for part in (
                completed.stdout,
                completed.stderr,
            )
            if part.strip()
        )
        or "No command output."
    )

    diagnostics_path: str | None = None

    if diagnostics_dir is not None:
        diagnostics_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        log_path = diagnostics_dir / f"{diagnostics_slug(name)}.log"

        log_path.write_text(
            "\n".join(
                [
                    f"Check: {name}",
                    f"Command: {' '.join(command)}",
                    f"Expected: {expected}",
                    f"Return code: {completed.returncode}",
                    "",
                    output,
                    "",
                ]
            ),
            encoding="utf-8",
        )

        try:
            diagnostics_path = str(log_path.relative_to(project_root))
        except ValueError:
            diagnostics_path = str(log_path)

    return CheckResult(
        name=name,
        expected=expected,
        status=("OK" if completed.returncode == 0 else "FAILED"),
        duration_seconds=round(duration, 4),
        details=output,
        command=list(command),
        diagnostics_path=diagnostics_path,
    )


def build_json_report(
    results: Sequence[CheckResult],
    generated_at: str,
) -> dict[str, Any]:
    return {
        "schema_version": ("logistics_service_check_report_v0_2"),
        "module_id": "logistics_service",
        "generated_at": generated_at,
        "overall_status": overall_status(results),
        "diagnostics_directory": "reports/diagnostics",
        "checks": [asdict(result) for result in results],
    }


def build_markdown_report(
    results: Sequence[CheckResult],
    generated_at: str,
) -> str:
    report_status = overall_status(results)

    rows = [
        ("| Check | Expected | Status | Time | Diagnostics |"),
        "|---|---|---:|---:|---|",
    ]

    for result in results:
        diagnostics = f"`{result.diagnostics_path}`" if result.diagnostics_path else "—"

        rows.append(
            f"| {result.name} | {result.expected} | "
            f"{markdown_status_text(result.status)} | "
            f"{result.duration_seconds:.4f}s | "
            f"{diagnostics} |"
        )

    return "\n".join(
        [
            ("# ForPrint Logistics Service — check report"),
            "",
            f"- Generated at: `{generated_at}`",
            f"- Overall status: `{report_status}`",
            "- Diagnostics: `reports/diagnostics/`",
            "",
            *rows,
            "",
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

    lines: list[str] = [
        colorize(
            ("ForPrint Logistics Service — check report"),
            ANSI_CYAN,
            use_color,
        ),
        "",
        _border(
            "┌",
            "┬",
            "┐",
            widths,
        ),
    ]

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

    statuses = [normalize_status(result.status) for result in results]

    passed_count = statuses.count("OK")
    warning_count = sum(status in {"WARN", "SKIPPED"} for status in statuses)
    failed_count = statuses.count("FAILED")
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


def build_full_console_output(
    results: Sequence[CheckResult],
    *,
    use_color: bool,
) -> str:
    sections = [
        build_console_summary(
            results,
            use_color=use_color,
        )
    ]

    for result in results:
        sections.extend(
            [
                "",
                "═" * 78,
                (f"{result.name}: {plain_status_text(result.status)}"),
                "Command: " + " ".join(result.command),
                ("Diagnostics: " + (result.diagnostics_path or "not written")),
                "─" * 78,
                result.details,
            ]
        )

    return "\n".join(sections)


def run_checks(
    project_root: Path,
    diagnostics_dir: Path | None = None,
) -> list[CheckResult]:
    return [
        run_command(
            name,
            command,
            expected,
            project_root,
            diagnostics_dir,
        )
        for name, command, expected in CHECK_COMMANDS
    ]


def remove_stale_diagnostics(
    diagnostics_dir: Path,
) -> None:
    diagnostics_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    for stale_log in diagnostics_dir.glob("*.log"):
        stale_log.unlink()


def write_reports(
    *,
    project_root: Path,
    results: Sequence[CheckResult],
    generated_at: str,
) -> tuple[Path, Path]:
    reports_dir = project_root / "reports"
    reports_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    json_path = reports_dir / "logistics_service_check_report.json"
    markdown_path = reports_dir / "logistics_service_check_report.md"

    json_report = build_json_report(
        results,
        generated_at,
    )
    markdown_report = build_markdown_report(
        results,
        generated_at,
    )

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

    return json_path, markdown_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description=("Run Logistics Service checks and generate stable reports.")
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
    parser.add_argument(
        "--full",
        action="store_true",
        help=("Print full command outputs after the compact summary."),
    )
    args = parser.parse_args()

    if args.list_checks:
        for name, command, _expected in CHECK_COMMANDS:
            print(f"{name}: {' '.join(command)}")

        return 0

    project_root = args.project_root.resolve()
    diagnostics_dir = project_root / "reports" / "diagnostics"

    remove_stale_diagnostics(diagnostics_dir)

    generated_at = datetime.now(UTC).isoformat()
    results = run_checks(
        project_root,
        diagnostics_dir,
    )

    json_path, markdown_path = write_reports(
        project_root=project_root,
        results=results,
        generated_at=generated_at,
    )

    use_color = color_enabled()

    if args.full:
        output = build_full_console_output(
            results,
            use_color=use_color,
        )
    else:
        output = build_console_summary(
            results,
            use_color=use_color,
        )

    print(output)
    print("")
    print(
        colorize(
            f"JSON report: {json_path}",
            ANSI_CYAN,
            use_color,
        )
    )
    print(
        colorize(
            f"Markdown report: {markdown_path}",
            ANSI_CYAN,
            use_color,
        )
    )
    print(
        colorize(
            (f"Diagnostics directory: {diagnostics_dir}"),
            ANSI_CYAN,
            use_color,
        )
    )

    return 1 if overall_status(results) == "FAILED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
