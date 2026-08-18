from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.diagnostics.run_logistics_checks import (  # noqa: E402
    build_console_summary,
    build_full_console_output,
    overall_status,
    run_checks,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Logistics checks without writing reports or diagnostics."
    )
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()

    results = run_checks(PROJECT_ROOT, diagnostics_dir=None)
    status = overall_status(results)

    if args.full:
        print(build_full_console_output(results, use_color=False))
    else:
        print(build_console_summary(results, use_color=False))
        if status != "OK":
            for result in results:
                if result.status == "FAILED":
                    print()
                    print("=" * 78)
                    print(f"FAILED CHECK: {result.name}")
                    print(f"Command: {' '.join(result.command)}")
                    print("-" * 78)
                    print(result.details)

    return 0 if status == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
