# Provider Adapter Contract Runbook

## Purpose

Verify and operate the provider-neutral contract without calling a real
provider or performing a provider-side write.

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

Local operational details may specialize these standards but cannot weaken
their requirements.

## Prerequisites

```bash
cd /srv/software_development/forprint-project/forprint_logistics_service
source .venv_logistics_service/bin/activate
git status -sb
git rev-parse HEAD
git rev-list --left-right --count HEAD...@{upstream}
```

Expected branch:

```text
feature/logistics-provider-adapter-contract-v01
```

Do not continue when unrelated working-tree changes exist.

## Safe operator workflow

```bash
make provider-contract-check
make provider-contract-preview
make check-report
make check-report-full
make governance-check
make module-validate
git diff --check
git status -sb
```

Every required validation command must return `0`.

## Provider contract validation

```bash
make provider-contract-check
```

Expected evidence:

```text
Four synthetic provider classes.
Typed recipient and address validation.
Preview-only shipment payload envelope.
Unsupported tracking and quote results.
Live provider writes remain disabled.
No real provider calls or credentials.
```

## Registry inspection

Implementation:

```text
app/adapters/providers/registry.py
app/adapters/providers/synthetic.py
```

Inspect through the deterministic local preview:

```bash
make provider-contract-preview
```

Review:

```text
reports/previews/provider_adapter_contract_preview.json
```

Only synthetic parcel, postal, freight and taxi/courier adapters are expected.

## Synthetic preview and fixtures

```bash
make provider-contract-preview
```

Required flags:

```text
preview_only = true
live_write = false
provider_call_performed = false
```

Fixture and test paths:

```text
app/adapters/providers/synthetic.py
tests/contract/fixtures/test_synthetic_provider_adapters.py
tests/integration/workflows/test_provider_adapter_preview.py
docs/development/testing/provider_contract_fixtures.md
```

## Report generation

Human-facing commands retain normal colors:

```bash
make check-report
make check-report-full
```

Artifacts:

```text
reports/logistics_service_check_report.json
reports/logistics_service_check_report.md
reports/diagnostics/
```

`NO_COLOR=1` is reserved for machine evidence or CI.

Cleanup:

```bash
make report-clean
```

## Verify live writes remain disabled

```bash
make provider-contract-check
.venv_logistics_service/bin/python -m pytest -q   tests/contract/adapters/test_provider_adapter_safety.py   tests/contract/fixtures/test_synthetic_provider_adapters.py   tests/integration/workflows/test_provider_adapter_preview.py   tests/unit/adapters/test_provider_registry.py   tests/unit/domain/test_provider_contracts.py   tests/unit/domain/test_provider_errors.py
```

The workflow is valid only when `create_shipment()` remains guarded and no
provider call is performed.

## Expected exits

| Command | Expected result | Exit |
|---|---|---:|
| `make provider-contract-check` | provider contract safe | 0 |
| `make provider-contract-preview` | local preview generated | 0 |
| `make check-report` | 10/10 checks | 0 |
| `make check-report-full` | extended diagnostics pass | 0 |
| `make governance-check` | governance passes | 0 |
| `make module-validate` | validation passes and reports are cleaned | 0 |
| direct pytest | collected set passes | 0 |
| `git diff --check` | no findings | 0 |

## Escalation conditions

Stop and escalate when:

- a provider hostname, SDK, HTTP client or credential appears;
- `live_write` or `provider_call_performed` becomes true;
- `create_shipment()` no longer raises the disabled-write error;
- registry resolution becomes non-deterministic;
- preview envelope compatibility breaks;
- fixtures contain real customer data;
- errors expose raw provider data;
- `module-validate` invokes itself or enables mutation;
- a required command returns non-zero;
- generated reports become staged or tracked unexpectedly.
