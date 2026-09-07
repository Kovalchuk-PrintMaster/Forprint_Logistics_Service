from __future__ import annotations

import argparse
import hashlib
import subprocess
from pathlib import Path
from typing import Any

import yaml

MODULE_ID = "logistics_service"
MEMORY_ROOT = Path("coordination/module_memory")
CURATED_FILES = (
    MEMORY_ROOT / "module_memory.yaml",
    MEMORY_ROOT / "implementation_lineage.yaml",
    MEMORY_ROOT / "document_authority.yaml",
    MEMORY_ROOT / "roadmap_state.yaml",
)
DERIVED_FILES = (
    MEMORY_ROOT / "inventory_index.yaml",
    MEMORY_ROOT / "current_state.yaml",
    MEMORY_ROOT / "fresh_context_manifest.yaml",
)
TOOL_FILES = (
    Path("AGENTS.md"),
    Path("Makefile"),
    Path("coordination/README.md"),
    Path("scripts/knowledge/build_module_memory_index.py"),
    Path("scripts/validation/validate_module_memory.py"),
    Path("scripts/validation/validate_document_authority.py"),
    Path("scripts/validation/validate_fresh_context.py"),
)
SNAPSHOT_FILES = (
    Path("coordination/blueprint_snapshot/current_release.yaml"),
    Path("coordination/blueprint_snapshot/prompt_queue.yaml"),
    Path(
        "coordination/blueprint_snapshot/prompts/approved/"
        "2026-09-05__logistics_service_authority_lineage_and_module_bootstrap_v0_1.md"
    ),
)
SELF_KNOWLEDGE_PREFIXES = (
    "AGENTS.md",
    "Makefile",
    "coordination/README.md",
    "coordination/module_memory/",
    "scripts/knowledge/",
    "scripts/validation/validate_module_memory.py",
    "scripts/validation/validate_document_authority.py",
    "scripts/validation/validate_fresh_context.py",
    "tests/coordination/test_module_self_knowledge_reference.py",
)
BLUEPRINT_SNAPSHOT_PREFIX = "coordination/blueprint_snapshot/"


class ModuleMemoryBuildError(RuntimeError):
    pass


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ModuleMemoryBuildError(f"missing YAML: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ModuleMemoryBuildError(f"YAML root must be mapping: {path}")
    return data


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode != 0:
        raise ModuleMemoryBuildError(f"git {' '.join(args)} failed: {result.stdout.strip()}")
    return result.stdout.strip()


def porcelain(root: Path) -> list[dict[str, str]]:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode != 0:
        raise ModuleMemoryBuildError(
            "git status failed: " + result.stdout.decode("utf-8", errors="replace").strip()
        )
    records = [item for item in result.stdout.split(b"\0") if item]
    parsed: list[dict[str, str]] = []
    index = 0
    while index < len(records):
        raw = records[index].decode("utf-8", errors="surrogateescape")
        if len(raw) < 4:
            raise ModuleMemoryBuildError(f"invalid porcelain record: {raw!r}")
        status = raw[:2]
        path = raw[3:]
        parsed.append({"status": status, "path": path})
        if status[0] in {"R", "C"}:
            index += 1
        index += 1
    return sorted(parsed, key=lambda item: (item["path"], item["status"]))


def classify_dirty(path: str) -> str:
    if path.startswith(BLUEPRINT_SNAPSHOT_PREFIX):
        return "blueprint_snapshot"
    for prefix in SELF_KNOWLEDGE_PREFIXES:
        if prefix.endswith("/") and path.startswith(prefix):
            return "self_knowledge"
        if path == prefix:
            return "self_knowledge"
    return "unclassified"


def ready_prompt(queue: dict[str, Any]) -> dict[str, Any]:
    rows = queue.get("prompt_queue")
    if not isinstance(rows, list):
        raise ModuleMemoryBuildError("prompt_queue must be list")
    ready: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        execution = row.get("module_execution")
        if isinstance(execution, dict) and execution.get("status") == "ready_for_module_pull":
            ready.append(row)
    ready.sort(
        key=lambda row: (
            int(row.get("sequence") or 0),
            str(row.get("prompt_id") or ""),
        )
    )
    if len(ready) == 1:
        row = ready[0]
        return {
            "state": "READY_PROMPT",
            "prompt_id": row.get("prompt_id"),
            "sequence": row.get("sequence"),
            "file": row.get("file"),
        }
    if not ready:
        return {"state": "NO_READY_PROMPT"}
    return {
        "state": "MULTIPLE_READY_PROMPTS",
        "prompt_ids": [row.get("prompt_id") for row in ready],
    }


def build_inventory_index(root: Path) -> dict[str, Any]:
    memory = load_yaml(root / MEMORY_ROOT / "module_memory.yaml")
    records = memory.get("records")
    if not isinstance(records, list):
        raise ModuleMemoryBuildError("module_memory.records must be list")

    implementations = []
    capabilities: dict[str, list[str]] = {}
    for record in records:
        if not isinstance(record, dict):
            raise ModuleMemoryBuildError("module memory record must be mapping")
        identity = record.get("identity")
        lifecycle = record.get("lifecycle")
        evidence = record.get("evidence")
        relationships = record.get("relationships")
        if not all(
            isinstance(item, dict) for item in (identity, lifecycle, evidence, relationships)
        ):
            raise ModuleMemoryBuildError(
                "record identity/lifecycle/evidence/relationships must be mappings"
            )
        implementation_id = str(identity.get("implementation_id"))
        capability_id = str(identity.get("capability_id"))
        implementations.append(
            {
                "implementation_id": implementation_id,
                "capability_id": capability_id,
                "implementation_kind": identity.get("implementation_kind"),
                "source_paths": sorted(identity.get("source_paths") or []),
                "lifecycle_state": lifecycle.get("lifecycle_state"),
                "documentation_refs": sorted(evidence.get("documentation_refs") or []),
                "test_refs": sorted(evidence.get("test_refs") or []),
                "contract_refs": sorted(evidence.get("contract_refs") or []),
                "dependencies": sorted(relationships.get("dependencies") or []),
                "consumers": sorted(relationships.get("consumers") or []),
            }
        )
        capabilities.setdefault(capability_id, []).append(implementation_id)

    implementations.sort(key=lambda item: item["implementation_id"])
    capability_rows = [
        {
            "capability_id": capability_id,
            "implementation_ids": sorted(implementation_ids),
        }
        for capability_id, implementation_ids in sorted(capabilities.items())
    ]

    return {
        "schema_version": "logistics_module_memory_inventory_index_v0_1",
        "module_id": MODULE_ID,
        "authority": "DERIVED_NAVIGATION_NOT_INDEPENDENT_AUTHORITY",
        "source": "coordination/module_memory/module_memory.yaml",
        "implementation_count": len(implementations),
        "capability_count": len(capability_rows),
        "capabilities": capability_rows,
        "implementations": implementations,
    }


def build_current_state(root: Path) -> dict[str, Any]:
    queue = load_yaml(root / "coordination/blueprint_snapshot/prompt_queue.yaml")
    release = load_yaml(root / "coordination/blueprint_snapshot/current_release.yaml")
    dirty = porcelain(root)
    categorized = [
        {
            **item,
            "classification": classify_dirty(item["path"]),
        }
        for item in dirty
    ]
    blueprint_snapshot = [
        item for item in categorized if item["classification"] == "blueprint_snapshot"
    ]
    unclassified = [item for item in categorized if item["classification"] == "unclassified"]
    release_data = release.get("release")
    progression = release.get("progression_gate_policy")
    scope = release.get("module_scope")
    if not all(isinstance(item, dict) for item in (release_data, progression, scope)):
        raise ModuleMemoryBuildError("current release snapshot shape is invalid")

    return {
        "schema_version": "logistics_module_memory_current_state_v0_1",
        "module_id": MODULE_ID,
        "authority": "DERIVED_CURRENT_STATE_PROJECTION",
        "git": {
            "branch": git(root, "branch", "--show-current"),
            "head": git(root, "rev-parse", "HEAD"),
        },
        "release": {
            "hardening_release": release_data.get("hardening_release"),
            "hardening_state": release_data.get("hardening_state"),
            "current_phase": progression.get("current_phase"),
            "pilot_module": scope.get("pilot_module"),
        },
        "prompt": ready_prompt(queue),
        "worker": {
            "dispatch_state": "PAUSED_BY_OPERATOR",
            "prompt_claim_created": False,
        },
        "working_tree": {
            "blueprint_snapshot_dirty_paths": blueprint_snapshot,
            "unclassified_dirty_paths": unclassified,
            "self_knowledge_changes_are_omitted_from_stability_signal": True,
        },
    }


def manifest_sources(root: Path) -> list[Path]:
    paths = [*CURATED_FILES, MEMORY_ROOT / "inventory_index.yaml", *TOOL_FILES, *SNAPSHOT_FILES]
    missing = [path.as_posix() for path in paths if not (root / path).is_file()]
    if missing:
        raise ModuleMemoryBuildError("fresh-context source files missing: " + ", ".join(missing))
    return paths


def build_fresh_context_manifest(root: Path) -> dict[str, Any]:
    current_state = build_current_state(root)
    source_rows = [
        {
            "path": path.as_posix(),
            "sha256": sha256(root / path),
        }
        for path in sorted(manifest_sources(root), key=lambda path: path.as_posix())
    ]
    return {
        "schema_version": "logistics_fresh_context_manifest_v0_1",
        "module_id": MODULE_ID,
        "authority": "DERIVED_FRESHNESS_EVIDENCE_NOT_PROMPT_AUTHORITY",
        "repository": current_state["git"],
        "prompt": current_state["prompt"],
        "worker_dispatch_state": "PAUSED_BY_OPERATOR",
        "unclassified_dirty_paths": current_state["working_tree"]["unclassified_dirty_paths"],
        "sources": source_rows,
    }


def write_yaml_if_changed(path: Path, data: dict[str, Any]) -> bool:
    payload = yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        width=112,
    )
    if path.is_file() and path.read_text(encoding="utf-8") == payload:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    return True


def build(root: Path) -> list[str]:
    changed: list[str] = []
    inventory = build_inventory_index(root)
    if write_yaml_if_changed(root / MEMORY_ROOT / "inventory_index.yaml", inventory):
        changed.append((MEMORY_ROOT / "inventory_index.yaml").as_posix())

    current = build_current_state(root)
    if write_yaml_if_changed(root / MEMORY_ROOT / "current_state.yaml", current):
        changed.append((MEMORY_ROOT / "current_state.yaml").as_posix())

    manifest = build_fresh_context_manifest(root)
    if write_yaml_if_changed(
        root / MEMORY_ROOT / "fresh_context_manifest.yaml",
        manifest,
    ):
        changed.append((MEMORY_ROOT / "fresh_context_manifest.yaml").as_posix())
    return sorted(changed)


def status(root: Path) -> str:
    current = build_current_state(root)
    memory = load_yaml(root / MEMORY_ROOT / "module_memory.yaml")
    records = memory.get("records")
    count = len(records) if isinstance(records, list) else 0
    prompt = current["prompt"]
    unclassified = current["working_tree"]["unclassified_dirty_paths"]
    lines = [
        "ForPrint Logistics self-knowledge status",
        "",
        f"module_id: {MODULE_ID}",
        f"branch: {current['git']['branch']}",
        f"head: {current['git']['head']}",
        f"module_memory_records: {count}",
        f"prompt_state: {prompt.get('state')}",
        f"prompt_id: {prompt.get('prompt_id', '-')}",
        "worker_dispatch_state: PAUSED_BY_OPERATOR",
        f"unclassified_dirty_path_count: {len(unclassified)}",
    ]
    if unclassified:
        lines.append("unclassified_dirty_paths:")
        for item in unclassified:
            lines.append(f"  - {item['status']} {item['path']}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("build", "status"))
    parser.add_argument("--module-root", default=".")
    args = parser.parse_args()

    root = Path(args.module_root).resolve()
    if args.action == "build":
        changed = build(root)
        print("MODULE_MEMORY_BUILD=PASS")
        print(f"CHANGED_COUNT={len(changed)}")
        for path in changed:
            print(f"CHANGED={path}")
        return 0

    print(status(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
