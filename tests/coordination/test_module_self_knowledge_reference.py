from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "scripts/knowledge/build_module_memory_index.py"


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "logistics_module_memory_builder_under_test",
        BUILDER,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_inventory_projection_is_deterministic():
    builder = load_builder()
    assert builder.build_inventory_index(ROOT) == builder.build_inventory_index(ROOT)


def test_current_state_has_no_unclassified_bootstrap_changes():
    builder = load_builder()
    state = builder.build_current_state(ROOT)
    assert state["working_tree"]["unclassified_dirty_paths"] == []
    assert state["worker"]["dispatch_state"] == "PAUSED_BY_OPERATOR"
    assert builder.classify_dirty("coordination/README.md") == "self_knowledge"


def test_module_memory_ids_are_unique():
    data = yaml.safe_load(
        (ROOT / "coordination/module_memory/module_memory.yaml").read_text(encoding="utf-8")
    )
    records = data["records"]
    ids = [record["identity"]["implementation_id"] for record in records]
    assert len(ids) == len(set(ids))
    assert len(ids) >= 5


def test_fresh_context_manifest_tracks_required_authority_sources():
    builder = load_builder()
    manifest = builder.build_fresh_context_manifest(ROOT)
    paths = {item["path"] for item in manifest["sources"]}
    assert "AGENTS.md" in paths
    assert "coordination/README.md" in paths
    assert "coordination/module_memory/module_memory.yaml" in paths
    assert "coordination/blueprint_snapshot/current_release.yaml" in paths
    assert "coordination/blueprint_snapshot/prompt_queue.yaml" in paths
