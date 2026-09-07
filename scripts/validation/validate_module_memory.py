from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
BUILDER_PATH = ROOT / "scripts/knowledge/build_module_memory_index.py"
_BUILDER_SPEC = importlib.util.spec_from_file_location(
    "logistics_module_memory_builder", BUILDER_PATH
)
if _BUILDER_SPEC is None or _BUILDER_SPEC.loader is None:
    raise RuntimeError(f"cannot load module-memory builder: {BUILDER_PATH}")
builder = importlib.util.module_from_spec(_BUILDER_SPEC)
_BUILDER_SPEC.loader.exec_module(builder)


MEMORY = ROOT / "coordination/module_memory/module_memory.yaml"
INDEX = ROOT / "coordination/module_memory/inventory_index.yaml"

REQUIRED_SECTIONS = {
    "identity",
    "purpose_and_provenance",
    "classification",
    "semantic_binding",
    "lifecycle",
    "lineage",
    "interfaces",
    "relationships",
    "evidence",
    "roadmap",
    "retirement",
    "freshness",
    "unknowns",
}
VALID_SCOPE = {"S0", "S1", "S2", "S3", "S4"}
VALID_CRITICALITY = {"C0", "C1", "C2", "C3", "C4"}
VALID_MATURITY = {
    "LOCAL",
    "OBSERVED",
    "PROVISIONAL",
    "RECOMMENDED",
    "CANONICAL",
    "DEPRECATED",
    "RETIRED",
}
VALID_LIFECYCLE = {
    "CURRENT",
    "SUPPORTED_LEGACY",
    "SPECIALIZED_CURRENT_REFERENCE",
    "HISTORICAL_REFERENCE",
    "PROVISIONAL",
    "DEPRECATED",
    "RETIRED",
    "UNKNOWN_LEGACY",
}


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be mapping: {path}")
    return data


def validate() -> list[str]:
    issues: list[str] = []
    if not (ROOT / "AGENTS.md").is_file():
        issues.append("root AGENTS.md is missing")
        return issues
    if not MEMORY.is_file():
        issues.append("module_memory.yaml is missing")
        return issues

    memory = load_yaml(MEMORY)
    if memory.get("schema_version") != "logistics_module_memory_v0_1":
        issues.append("module_memory schema_version is invalid")
    if memory.get("module_id") != "logistics_service":
        issues.append("module_id must be logistics_service")

    records = memory.get("records")
    if not isinstance(records, list) or not records:
        issues.append("module_memory.records must be non-empty list")
        return issues

    implementation_ids: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            issues.append(f"record {index} must be mapping")
            continue
        missing_sections = REQUIRED_SECTIONS - set(record)
        if missing_sections:
            issues.append(f"record {index} missing sections: {sorted(missing_sections)}")
            continue
        identity = record.get("identity")
        classification = record.get("classification")
        lifecycle = record.get("lifecycle")
        provenance = record.get("purpose_and_provenance")
        evidence = record.get("evidence")
        unknowns = record.get("unknowns")
        if not all(
            isinstance(item, dict)
            for item in (
                identity,
                classification,
                lifecycle,
                provenance,
                evidence,
                unknowns,
            )
        ):
            issues.append(f"record {index} has invalid section shapes")
            continue

        implementation_id = identity.get("implementation_id")
        if not isinstance(implementation_id, str) or not implementation_id:
            issues.append(f"record {index} implementation_id missing")
        elif implementation_id in implementation_ids:
            issues.append(f"duplicate implementation_id: {implementation_id}")
        else:
            implementation_ids.add(implementation_id)

        if classification.get("interaction_scope") not in VALID_SCOPE:
            issues.append(f"{implementation_id}: invalid interaction_scope")
        if classification.get("criticality") not in VALID_CRITICALITY:
            issues.append(f"{implementation_id}: invalid criticality")
        if classification.get("standardization_maturity") not in VALID_MATURITY:
            issues.append(f"{implementation_id}: invalid standardization_maturity")
        if lifecycle.get("lifecycle_state") not in VALID_LIFECYCLE:
            issues.append(f"{implementation_id}: invalid lifecycle_state")

        for source in identity.get("source_paths") or []:
            if not isinstance(source, str) or not (ROOT / source).is_file():
                issues.append(f"{implementation_id}: source path does not exist: {source!r}")

        for key in ("documentation_refs", "test_refs", "contract_refs"):
            for ref in evidence.get(key) or []:
                if not isinstance(ref, str):
                    issues.append(f"{implementation_id}: invalid {key} reference")
                    continue
                if ref.startswith("blueprint://"):
                    continue
                if not (ROOT / ref).is_file():
                    issues.append(f"{implementation_id}: {key} path does not exist: {ref}")

        if lifecycle.get("lifecycle_state") == "UNKNOWN_LEGACY":
            if provenance.get("purpose") != "UNKNOWN_LEGACY":
                issues.append(f"{implementation_id}: UNKNOWN_LEGACY purpose must stay explicit")
            if provenance.get("provenance_confidence") not in {"low", "unknown"}:
                issues.append(
                    f"{implementation_id}: unknown legacy provenance cannot be high confidence"
                )
            if unknowns.get("review_required") is not True:
                issues.append(f"{implementation_id}: unknown legacy record must require review")

    if INDEX.is_file():
        expected = builder.build_inventory_index(ROOT)
        observed = load_yaml(INDEX)
        if observed != expected:
            issues.append("inventory_index.yaml is stale; run make module-memory-build")
    else:
        issues.append("inventory_index.yaml is missing")

    return issues


def main() -> int:
    issues = validate()
    if issues:
        print("MODULE_MEMORY_VALIDATION=FAIL")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("MODULE_MEMORY_VALIDATION=PASS")
    print(f"IMPLEMENTATION_RECORD_COUNT={len(load_yaml(MEMORY)['records'])}")
    print("ROOT_AGENTS=PASS")
    print("INVENTORY_INDEX=FRESH")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
