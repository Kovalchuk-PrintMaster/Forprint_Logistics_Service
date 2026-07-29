from pathlib import Path

from scripts.diagnostics.run_logistics_checks import CHECK_COMMANDS

MAKEFILE_PATH = Path("Makefile")


def target_recipe(text: str, target: str) -> str:
    source_lines = text.splitlines()
    target_line = f"{target}:"

    try:
        start_index = source_lines.index(target_line) + 1
    except ValueError as exc:
        raise AssertionError(f"Make target not found: {target}") from exc

    recipe_lines: list[str] = []

    for line in source_lines[start_index:]:
        if not line.strip():
            if recipe_lines:
                break
            continue

        if not line.startswith(("\t", " ")):
            break

        recipe_lines.append(line.strip())

    return "\n".join(recipe_lines)


def test_tracking_events_make_targets_are_canonical() -> None:
    text = MAKEFILE_PATH.read_text(encoding="utf-8")

    assert "tracking-events-check:" in text
    assert "tracking-events-preview:" in text
    assert '@echo "  make tracking-events-check"' in text
    assert '@echo "  make tracking-events-preview"' in text

    check_recipe = target_recipe(text, "check")
    assert "$(MAKE) tracking-events-check" in check_recipe

    preview_recipe = target_recipe(
        text,
        "tracking-events-preview",
    )
    assert "$(PYTHON) -m scripts.previews.preview_tracking_events_contract" in preview_recipe


def test_check_report_includes_tracking_events_once() -> None:
    matching = [item for item in CHECK_COMMANDS if item[0] == "Tracking events"]

    assert len(matching) == 1
    assert matching[0][1] == (
        "make",
        "tracking-events-check",
    )
    assert len(CHECK_COMMANDS) == 11
