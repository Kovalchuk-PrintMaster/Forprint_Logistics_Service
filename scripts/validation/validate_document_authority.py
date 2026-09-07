from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
AUTHORITY = ROOT / "coordination/module_memory/document_authority.yaml"
VALID_CLASSES = {
    "CURRENT_AUTHORITY",
    "CURRENT_SUPPORTING",
    "HISTORICAL_EVIDENCE",
    "GENERATED_RUNTIME_SNAPSHOT",
}


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be mapping: {path}")
    return data


def validate() -> list[str]:
    issues: list[str] = []
    data = load_yaml(AUTHORITY)
    if data.get("schema_version") != "logistics_document_authority_v0_1":
        issues.append("invalid document authority schema_version")
    rows = data.get("documents")
    if not isinstance(rows, list) or not rows:
        return issues + ["documents must be a non-empty list"]

    paths: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            issues.append("document authority row must be mapping")
            continue
        path = row.get("path")
        classification = row.get("classification")
        if not isinstance(path, str) or not path:
            issues.append("document authority path missing")
            continue
        if path in paths:
            issues.append(f"duplicate document authority path: {path}")
        paths.add(path)
        if classification not in VALID_CLASSES:
            issues.append(f"{path}: invalid classification {classification!r}")
        if not (ROOT / path).is_file():
            issues.append(f"{path}: document does not exist")
        if classification == "HISTORICAL_EVIDENCE" and row.get("execution_authority") is True:
            issues.append(f"{path}: historical evidence cannot be execution authority")

    return issues


def main() -> int:
    issues = validate()
    if issues:
        print("DOCUMENT_AUTHORITY_VALIDATION=FAIL")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("DOCUMENT_AUTHORITY_VALIDATION=PASS")
    print(f"DOCUMENT_COUNT={len(load_yaml(AUTHORITY)['documents'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
