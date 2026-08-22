from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MAKEFILE_PATH = PROJECT_ROOT / "Makefile"


def recipe(target: str) -> tuple[str, ...]:
    lines = MAKEFILE_PATH.read_text(encoding="utf-8").splitlines()
    start = lines.index(f"{target}:") + 1
    result = []
    for line in lines[start:]:
        if line.startswith("\t"):
            result.append(line.strip())
        elif result:
            break
    return tuple(result)


def test_module_start_uses_h9_exact_order() -> None:
    assert recipe("module-start") == (
        "$(MAKE) coordination-sync-check",
        "$(MAKE) module-sync",
        "$(MAKE) module-status",
        "$(MAKE) prompt-notify",
        "$(MAKE) prompt-read-next",
    )


def test_module_sync_is_network_independent() -> None:
    assert recipe("module-sync") == (
        "$(MAKE) module-sync-apply",
        "$(MAKE) document-awareness",
        "$(MAKE) coordination-check",
        "$(MAKE) module-status",
    )


def test_blueprint_pull_is_fail_closed() -> None:
    joined = "\n".join(recipe("blueprint-pull"))
    assert "pull --ff-only" not in joined
    assert "deprecated" in joined.lower()
    assert "exit 2" in joined


def test_canonical_surface_is_exposed() -> None:
    text = MAKEFILE_PATH.read_text(encoding="utf-8")
    for target in (
        "module-start",
        "module-sync",
        "module-status",
        "module-validate",
        "coordination-sync-check",
        "blueprint-check",
        "blueprint-prompts-list",
        "prompt-notify",
        "prompt-next",
        "prompt-read-next",
        "check",
        "governance-check",
        "git-status",
    ):
        assert f"{target}:" in text


def test_coordination_check_does_not_execute_blueprint_python() -> None:
    joined = "\n".join(recipe("coordination-check"))
    assert "BLUEPRINT_PYTHON" not in joined
    assert "check_coordination_metadata.py" not in joined


def test_deterministic_checks_do_not_call_freshness_gate() -> None:
    for target in ("check", "governance-check", "module-validate"):
        assert "coordination-sync-check" not in "\n".join(recipe(target))
