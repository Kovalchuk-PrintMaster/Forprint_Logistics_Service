from pathlib import Path

import yaml


def test_env_example_contains_no_provider_credentials() -> None:
    lines = Path(".env.example").read_text(encoding="utf-8").splitlines()

    sensitive_prefixes = (
        "FORPRINT_LOGISTICS_NOVA_POSHTA_API_KEY=",
        "FORPRINT_LOGISTICS_UKRPOSHTA_API_TOKEN=",
        "FORPRINT_LOGISTICS_MEEST_API_TOKEN=",
        "FORPRINT_LOGISTICS_SAT_API_TOKEN=",
    )

    values = {
        line.split("=", maxsplit=1)[0]: line.split("=", maxsplit=1)[1]
        for line in lines
        if line.startswith(sensitive_prefixes)
    }

    assert values
    assert all(value == "" for value in values.values())


def test_provider_example_references_environment_variable_names_only() -> None:
    data = yaml.safe_load(Path("config/providers.example.yaml").read_text(encoding="utf-8"))

    assert data["live_provider_writes_enabled"] is False

    for provider in data["providers"]:
        assert provider["live_write_enabled"] is False

        credential_reference = provider["credential_environment_variable"]

        if credential_reference is not None:
            assert credential_reference.startswith("FORPRINT_LOGISTICS_")
