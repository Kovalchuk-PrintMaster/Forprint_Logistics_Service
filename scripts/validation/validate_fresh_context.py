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


CURRENT_STATE = ROOT / "coordination/module_memory/current_state.yaml"
MANIFEST = ROOT / "coordination/module_memory/fresh_context_manifest.yaml"


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be mapping: {path}")
    return data


def validate() -> list[str]:
    issues: list[str] = []
    if not CURRENT_STATE.is_file():
        issues.append("current_state.yaml missing")
    if not MANIFEST.is_file():
        issues.append("fresh_context_manifest.yaml missing")
    if issues:
        return issues

    expected_state = builder.build_current_state(ROOT)
    observed_state = load_yaml(CURRENT_STATE)
    if observed_state != expected_state:
        issues.append("current_state.yaml is stale; run make module-memory-build")

    expected_manifest = builder.build_fresh_context_manifest(ROOT)
    observed_manifest = load_yaml(MANIFEST)
    if observed_manifest != expected_manifest:
        issues.append("fresh_context_manifest.yaml is stale; run make module-memory-build")

    unclassified = expected_manifest.get("unclassified_dirty_paths")
    if not isinstance(unclassified, list):
        issues.append("fresh context unclassified_dirty_paths must be list")
    elif unclassified:
        for item in unclassified:
            issues.append(
                "unclassified working-tree change blocks fresh context: "
                + f"{item.get('status')} {item.get('path')}"
            )

    prompt = expected_manifest.get("prompt")
    if not isinstance(prompt, dict) or prompt.get("state") != "READY_PROMPT":
        issues.append("exactly one ready prompt is required for current H10 pilot baseline")

    if expected_manifest.get("worker_dispatch_state") != "PAUSED_BY_OPERATOR":
        issues.append("worker dispatch must remain paused during self-knowledge bootstrap")

    return issues


def main() -> int:
    issues = validate()
    if issues:
        print("FRESH_CONTEXT_VALIDATION=FAIL")
        for issue in issues:
            print(f"- {issue}")
        return 1
    manifest = load_yaml(MANIFEST)
    print("FRESH_CONTEXT_VALIDATION=PASS")
    print(f"MODULE_HEAD={manifest['repository']['head']}")
    print(f"PROMPT_STATE={manifest['prompt']['state']}")
    print(f"PROMPT_ID={manifest['prompt'].get('prompt_id')}")
    print("WORKER_DISPATCH_STATE=PAUSED_BY_OPERATOR")
    print("UNCLASSIFIED_DIRTY_PATH_COUNT=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
