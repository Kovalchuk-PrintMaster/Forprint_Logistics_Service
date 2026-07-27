# Provider Adapter Contract Recovery Guide

## Purpose

Recover the accepted provider-neutral contract without a real provider call or
provider-side write.

This document is provider-specific. Reporting recovery remains in
`docs/operations/check_reporting_recovery.md`.

## Policy sources

Blueprint standards are referenced, not copied.

| Purpose | Source | Authority |
|---|---|---|
| provider-adapter local rules | `docs/architecture/adapters/provider_adapter_policy.md` | module-local specialization |
| prompt execution and reporting | `coordination/standards/governance/module_prompt_execution_and_reporting_protocol.md` | Blueprint canonical standard |
| check-report behavior | `coordination/standards/testing_and_check_report_standard.md` | Blueprint canonical standard |
| recovery and documentation gate | `coordination/standards/governance/documentation_and_recovery_gate.md` | Blueprint canonical standard |
| operator and Make workflow | `coordination/standards/make_command_standard.md` | Blueprint canonical standard |
| module Make target contract | `coordination/standards/module_make_target_contract.md` | Blueprint canonical standard |

Local recovery steps cannot weaken Blueprint safety or repository ownership.

## Accepted recovery points

```text
acceptance-closeout base: 4c58be61529a8e8b715b94adb8f7c28691e6da43
completion commit: db614b72173ac9ad387cfdd76adae7dfacc519ab
implementation commit: 245fea7c868be675b844885a55070712cfa81db2
```

## Establish state

```bash
git status -sb
git branch --show-current
git rev-parse HEAD
git log -5 --oneline
```

Create a recovery branch before restoring files:

```bash
git switch -c recovery/provider-adapter-contract-v0-1
```

## Restore accepted provider files

```bash
ACCEPTED_COMMIT="4c58be61529a8e8b715b94adb8f7c28691e6da43"

git restore --source "$ACCEPTED_COMMIT" --   app/domain/provider_contracts.py   app/domain/provider_errors.py   app/domain/providers.py   app/adapters/providers/base.py   app/adapters/providers/registry.py   app/adapters/providers/synthetic.py   scripts/previews/preview_provider_adapter_contract.py   scripts/validation/check_provider_adapter_contract.py   tests/contract/adapters/test_provider_adapter_safety.py   tests/contract/fixtures/test_synthetic_provider_adapters.py   tests/integration/workflows/test_provider_adapter_preview.py   tests/unit/adapters/test_provider_registry.py   tests/unit/domain/test_provider_contracts.py   tests/unit/domain/test_provider_errors.py
```

Review before commit:

```bash
git diff --check
git diff --stat
git diff
```

Do not use `git reset --hard` as the routine recovery path.

## Registry regression

Restore:

```bash
git restore --source "$ACCEPTED_COMMIT" --   app/adapters/providers/registry.py   app/adapters/providers/synthetic.py   tests/unit/adapters/test_provider_registry.py   tests/contract/fixtures/test_synthetic_provider_adapters.py
```

Verify:

```bash
.venv_logistics_service/bin/python -m pytest -q   tests/unit/adapters/test_provider_registry.py   tests/contract/fixtures/test_synthetic_provider_adapters.py
```

## Incompatible preview envelope

Restore:

```bash
git restore --source "$ACCEPTED_COMMIT" --   app/domain/provider_contracts.py   app/adapters/providers/base.py   scripts/previews/preview_provider_adapter_contract.py   tests/unit/domain/test_provider_contracts.py   tests/integration/workflows/test_provider_adapter_preview.py
```

Verify:

```bash
make provider-contract-preview
make provider-contract-check
```

## Fixture or error-taxonomy regression

```bash
git restore --source "$ACCEPTED_COMMIT" --   app/adapters/providers/synthetic.py   app/domain/provider_errors.py   tests/contract/fixtures/test_synthetic_provider_adapters.py   tests/unit/domain/test_provider_errors.py
```

Verify safe messages, retryability and absence of sensitive raw data.

## Live-write guard enabled

Treat this as an immediate stop condition. Do not run external or provider
commands.

Inspect:

```bash
git diff --   app/adapters/providers/base.py   app/domain/provider_contracts.py   scripts/previews/preview_provider_adapter_contract.py
```

Restore:

```bash
git restore --source "$ACCEPTED_COMMIT" --   app/adapters/providers/base.py   app/domain/provider_contracts.py   scripts/previews/preview_provider_adapter_contract.py   tests/contract/adapters/test_provider_adapter_safety.py   tests/integration/workflows/test_provider_adapter_preview.py
```

Verify:

```bash
make provider-contract-check
.venv_logistics_service/bin/python -m pytest -q   tests/contract/adapters/test_provider_adapter_safety.py   tests/integration/workflows/test_provider_adapter_preview.py
```

Required invariants:

```text
preview_only = true
live_write = false
provider_call_performed = false
create_shipment raises LiveProviderWriteDisabledError
```

## Full verification after recovery

```bash
make provider-contract-check
make check-report
make check-report-full
make governance-check
make module-validate

.venv_logistics_service/bin/python -m pytest --collect-only -q
.venv_logistics_service/bin/python -m pytest -q

git diff --check
git status -sb
```

All required commands must return `0`.

## Confirm no external call or write occurred

Confirm:

- no provider SDK or HTTP client was added;
- no credential or endpoint was configured;
- no real provider call occurred;
- no shipment, TTN, courier or taxi object was created;
- no production storage, queue or worker was introduced;
- `provider_call_performed = false`;
- `live_write = false`.

Escalate any transport, credential or provider-write change.
