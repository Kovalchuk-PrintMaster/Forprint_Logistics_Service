from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MAKEFILE_PATH = PROJECT_ROOT / "Makefile"


def target_recipe_lines(
    makefile_text: str,
    target: str,
) -> tuple[str, ...]:
    lines = makefile_text.splitlines()
    target_line = f"{target}:"

    try:
        start = lines.index(target_line) + 1
    except ValueError as exc:
        raise AssertionError(f"Make target is missing: {target}") from exc

    recipe: list[str] = []

    for line in lines[start:]:
        if line.startswith("\t"):
            recipe.append(line.strip())
            continue

        if recipe:
            break

    return tuple(recipe)


def test_module_start_uses_standard_local_workflow() -> None:
    text = MAKEFILE_PATH.read_text(encoding="utf-8")
    recipe = target_recipe_lines(
        text,
        "module-start",
    )

    assert recipe == (
        "$(MAKE) blueprint-check",
        "$(MAKE) blueprint-standards-check",
        "$(MAKE) blueprint-sync-directives",
        "$(MAKE) blueprint-prompts-sync",
        "$(MAKE) coordination-check",
        "$(MAKE) status-report",
        "$(MAKE) blueprint-prompt",
    )

    assert "$(MAKE) blueprint-pull" not in recipe


def test_module_sync_does_not_read_active_prompt() -> None:
    text = MAKEFILE_PATH.read_text(encoding="utf-8")
    recipe = target_recipe_lines(
        text,
        "module-sync",
    )

    assert recipe == (
        "$(MAKE) blueprint-check",
        "$(MAKE) blueprint-standards-check",
        "$(MAKE) blueprint-sync-directives",
        "$(MAKE) blueprint-prompts-sync",
        "$(MAKE) coordination-check",
        "$(MAKE) status-report",
    )

    assert "$(MAKE) blueprint-prompt" not in recipe


def test_help_exposes_module_workflow() -> None:
    text = MAKEFILE_PATH.read_text(encoding="utf-8")

    assert '@echo "  make module-start"' in text
    assert '@echo "  make module-sync"' in text
    assert '@echo "  make module-validate"' in text


def test_module_validate_composes_existing_safe_targets() -> None:
    text = MAKEFILE_PATH.read_text(encoding="utf-8")
    recipe = target_recipe_lines(
        text,
        "module-validate",
    )

    assert recipe == (
        "$(MAKE) check-report-full",
        "$(MAKE) governance-check",
        "$(MAKE) report-clean",
        "$(MAKE) status-report",
    )
    assert "$(MAKE) module-validate" not in recipe

    for target in (
        "check-report-full",
        "governance-check",
        "report-clean",
        "status-report",
    ):
        assert f"{target}:" in text

    forbidden_tokens = (
        "curl ",
        "wget ",
        "requests.",
        "httpx.",
        "create_shipment",
        "live_write=true",
        "live_write = true",
        "credentials",
    )
    recipe_text = "\n".join(recipe).lower()

    for token in forbidden_tokens:
        assert token not in recipe_text

    report_clean_text = "\n".join(
        target_recipe_lines(
            text,
            "report-clean",
        )
    )

    assert "reports/logistics_service_check_report.json" in (report_clean_text)
    assert "reports/logistics_service_check_report.md" in (report_clean_text)
    assert "reports/diagnostics" in report_clean_text
    assert recipe[-2:] == (
        "$(MAKE) report-clean",
        "$(MAKE) status-report",
    )
