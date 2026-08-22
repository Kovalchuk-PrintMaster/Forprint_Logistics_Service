from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = PROJECT_ROOT / "scripts/validation/check_project_policies.py"


def _scripts_allowed_root_files() -> set[str]:
    tree = ast.parse(POLICY_PATH.read_text(encoding="utf-8"))

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name != "_check_flat_directory_policy":
            continue

        for child in ast.walk(node):
            if not isinstance(child, ast.Assign):
                continue
            if len(child.targets) != 1:
                continue
            target = child.targets[0]
            if not (isinstance(target, ast.Name) and target.id == "allowed_root_files"):
                continue
            if not isinstance(child.value, ast.Dict):
                raise AssertionError("allowed_root_files must remain a literal dict")

            for key, value in zip(
                child.value.keys,
                child.value.values,
                strict=True,
            ):
                if not (isinstance(key, ast.Constant) and key.value == "scripts"):
                    continue
                if not isinstance(value, ast.Set):
                    raise AssertionError("scripts root allowance must remain a literal set")
                return {
                    item.value
                    for item in value.elts
                    if isinstance(item, ast.Constant) and isinstance(item.value, str)
                }

    raise AssertionError("scripts root allowance was not found in _check_flat_directory_policy")


def test_h9_checker_is_the_only_new_scripts_root_exception() -> None:
    assert _scripts_allowed_root_files() == {
        "__init__.py",
        "coordination_sync_check.py",
    }


def test_arbitrary_scripts_root_python_remains_forbidden() -> None:
    allowed = _scripts_allowed_root_files()
    assert "foo.py" not in allowed
    assert "temporary_helper.py" not in allowed
    assert "module_sync.py" not in allowed
