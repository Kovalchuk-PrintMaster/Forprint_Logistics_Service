from __future__ import annotations

import copy
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


def _normalize_provenance_head(
    data: dict[str, Any],
    section: str,
) -> dict[str, Any] | None:
    """Return a deep-copied projection with only the Git HEAD value normalized.

    Git HEAD is provenance evidence, not a freshness key. A commit containing
    freshly generated projections necessarily changes HEAD after generation.
    Branch, prompt, worker state, dirty-path state, source hashes and all other
    fields remain strict freshness inputs.
    """
    normalized = copy.deepcopy(data)
    repository = normalized.get(section)
    if not isinstance(repository, dict):
        return None

    head = repository.get("head")
    if not isinstance(head, str) or not head:
        return None

    repository["head"] = "<PROVENANCE_HEAD>"
    return normalized


def current_state_matches_for_freshness(
    observed: dict[str, Any],
    expected: dict[str, Any],
) -> bool:
    observed_normalized = _normalize_provenance_head(observed, "git")
    expected_normalized = _normalize_provenance_head(expected, "git")
    return (
        observed_normalized is not None
        and expected_normalized is not None
        and observed_normalized == expected_normalized
    )


def manifest_matches_for_freshness(
    observed: dict[str, Any],
    expected: dict[str, Any],
) -> bool:
    observed_normalized = _normalize_provenance_head(observed, "repository")
    expected_normalized = _normalize_provenance_head(expected, "repository")
    return (
        observed_normalized is not None
        and expected_normalized is not None
        and observed_normalized == expected_normalized
    )


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
    if not current_state_matches_for_freshness(observed_state, expected_state):
        issues.append("current_state.yaml is stale; run make module-memory-build")

    expected_manifest = builder.build_fresh_context_manifest(ROOT)
    observed_manifest = load_yaml(MANIFEST)
    if not manifest_matches_for_freshness(observed_manifest, expected_manifest):
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
