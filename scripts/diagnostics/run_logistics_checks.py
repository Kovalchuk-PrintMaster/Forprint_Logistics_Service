from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CHECK_COMMANDS: tuple[tuple[str, tuple[str, ...], str], ...] = (
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
        part.strip() for part in (completed.stdout, completed.stderr) if part.strip()
    )

    return CheckResult(
        name=name,
        expected=expected,
        status="OK" if completed.returncode == 0 else "FAILED",
        duration_seconds=round(duration, 4),
        details=output or "No command output.",
        command=list(command),
    )


def build_json_report(
    results: Sequence[CheckResult],
    generated_at: str,
) -> dict[str, Any]:
    overall_status = "FAILED" if any(result.status == "FAILED" for result in results) else "OK"

    return {
        "module_id": "logistics_service",
        "generated_at": generated_at,
        "overall_status": overall_status,
        "checks": [asdict(result) for result in results],
    }


def build_markdown_report(
    results: Sequence[CheckResult],
    generated_at: str,
) -> str:
    overall_status = "FAILED" if any(result.status == "FAILED" for result in results) else "OK"

    rows = [
        "| Check | Expected | Status | Time |",
        "|---|---|---:|---:|",
    ]

    for result in results:
        rows.append(
            f"| {result.name} | {result.expected} | "
            f"{result.status} | {result.duration_seconds:.4f}s |"
        )

    details: list[str] = []

    for result in results:
        details.extend(
            [
                f"## {result.name}",
                "",
                f"- Status: `{result.status}`",
                f"- Command: `{' '.join(result.command)}`",
                "",
                "```text",
                result.details,
                "```",
                "",
            ]
        )

    return "\n".join(
        [
            "# ForPrint Logistics Service — check report",
            "",
            f"- Generated at: `{generated_at}`",
            f"- Overall status: `{overall_status}`",
            "",
            *rows,
            "",
            *details,
        ]
    )


def _print_console_summary(results: Sequence[CheckResult]) -> None:
    print("ForPrint Logistics Service — check report")
    print("")

    for result in results:
        print(f"[{result.status:<6}] {result.name:<24} {result.duration_seconds:>8.4f}s")

    failed = [result for result in results if result.status == "FAILED"]

    print("")

    if failed:
        print(f"Overall status: FAILED ({len(failed)} failed check(s))")
    else:
        print("Overall status: OK")


def run_checks(project_root: Path) -> list[CheckResult]:
    return [
        run_command(name, command, expected, project_root)
        for name, command, expected in CHECK_COMMANDS
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Logistics Service checks and generate reports."
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
    reports_dir.mkdir(parents=True, exist_ok=True)

    generated_at = datetime.now(UTC).isoformat()
    results = run_checks(project_root)

    json_report = build_json_report(results, generated_at)
    markdown_report = build_markdown_report(results, generated_at)

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
