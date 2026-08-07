from __future__ import annotations

import ast
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REQUIRED_CONFIRMATIONS = (
    "no_automatic_posting",
    "no_live_external_integrations",
    "no_production_api",
    "no_production_write",
    "no_real_1c_sync",
)
NETWORK_IMPORTS = {"aiohttp", "httpx", "requests", "urllib3"}
API_IMPORTS = {"django", "fastapi", "flask", "litestar", "sanic", "starlette"}
ONE_C_IMPORTS = {"onec", "onec_api", "py1c"}
TRUE_PATTERNS = {
    "no_production_write": re.compile(
        r"(?im)^\s*(?:live_write|production_write|provider_write_enabled)\s*[:=]\s*true\s*$"
    ),
    "no_automatic_posting": re.compile(
        r"(?im)^\s*(?:automatic_posting|auto_posting|automatic_post)\s*[:=]\s*true\s*$"
    ),
    "no_real_1c_sync": re.compile(
        r"(?im)^\s*(?:real_1c_sync|one_c_sync_enabled|onec_sync_enabled|one_c_write|onec_write)\s*[:=]\s*true\s*$"
    ),
}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def validate_boundaries() -> list[str]:
    findings: list[str] = []
    roots = (
        PROJECT_ROOT / "app",
        PROJECT_ROOT / "config",
        PROJECT_ROOT / "examples/fixtures/tracking_events",
    )
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        files.extend(
            path
            for path in root.rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix in {".py", ".yaml", ".yml", ".toml", ".ini", ".env"}
        )
    for path in sorted(set(files)):
        relative = path.relative_to(PROJECT_ROOT)
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".py":
            imports = _imports(path)
            if imports & NETWORK_IMPORTS:
                network_imports = sorted(imports & NETWORK_IMPORTS)
                findings.append(f"no_live_external_integrations: {relative}: {network_imports}")
            if imports & API_IMPORTS:
                findings.append(f"no_production_api: {relative}: {sorted(imports & API_IMPORTS)}")
            if imports & ONE_C_IMPORTS:
                findings.append(f"no_real_1c_sync: {relative}: {sorted(imports & ONE_C_IMPORTS)}")
        for boundary, pattern in TRUE_PATTERNS.items():
            if match := pattern.search(text):
                findings.append(f"{boundary}: {relative}: {match.group(0).strip()}")
    return findings


def main() -> int:
    findings = validate_boundaries()
    print("ForPrint Logistics Service — completion safety boundary validation")
    print("")
    if findings:
        for finding in findings:
            print(f"[FAILED] {finding}")
        return 1
    for name in REQUIRED_CONFIRMATIONS:
        print(f"[OK] {name}: true")
    print("")
    print("[OK] No implementation evidence contradicts the required positive safety confirmations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
