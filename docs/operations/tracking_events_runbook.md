# Tracking Events Runbook

## Purpose

Operate and verify the provider-neutral tracking event contract without
provider calls, Telegram calls, production persistence or cross-repository
writes.

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
feature/logistics-tracking-events-contract-v01
```

Do not continue when unrelated working-tree changes exist.

## Authoritative paths

```text
app/domain/tracking.py
app/domain/events.py
app/services/tracking_contract_service.py
examples/fixtures/tracking_events/synthetic_tracking_events.yaml
scripts/validation/check_tracking_events_contract.py
scripts/previews/preview_tracking_events_contract.py
```

## Focused contract check

```bash
make tracking-events-check
```

Expected evidence:

```text
Six canonical provider-neutral event types.
Typed versioned event envelopes.
Deterministic lifecycle transitions.
Duplicate and out-of-order observations.
Failure and human-attention scenarios.
Channel-neutral notification projections.
Stable event and notification idempotency.
Synthetic fixture contains no credentials or real data.
Preview-only execution with no external calls or writes.
```

Expected exit:

```text
0
```

## Read-only preview

```bash
make tracking-events-preview
```

The canonical Make preview builds all scenarios in process memory and does not
write to the filesystem.

Explicit artifact generation is separate:

```bash
make tracking-events-preview-generate
```

Generated artifact:

```text
reports/previews/tracking_events_contract_preview.json
```

Review generated top-level safety evidence after the explicit generation command:

```bash
grep -nE \
  '"preview_only"|"live_write"|"provider_call_performed"|"telegram_api_call_performed"|"cross_repository_write"|"notification_replay_stable"' \
  reports/previews/tracking_events_contract_preview.json
```

Expected values:

```text
notification_replay_stable = true
preview_only = true
live_write = false
provider_call_performed = false
telegram_api_call_performed = false
cross_repository_write = false
```

The preview contains no provider, Telegram or cross-repository execution.

## Focused tests

```bash
.venv_logistics_service/bin/python -m pytest \
  -q \
  -o addopts='' \
  tests/unit/domain/test_tracking_event_contract.py \
  tests/unit/services/test_tracking_contract_service.py \
  tests/contract/fixtures/test_tracking_events_fixture.py \
  tests/contract/policies/test_tracking_events_make_targets.py \
  tests/contract/policies/test_tracking_events_documentation.py \
  tests/integration/workflows/test_tracking_events_preview.py \
  tests/integration/workflows/test_tracking_events_check_visibility.py
```

## Full validation

```bash
make tracking-events-check
make check
make check-report
make check-report-full
make governance-check
make module-validate
git diff --check
git status -sb
```

Every required command must return `0`.

`check-report` and `check-report-full` contain eleven checks, including the
focused `Tracking events` check.

## Test evidence

Record exact test collection separately from check-report totals:

```bash
.venv_logistics_service/bin/python -m pytest --collect-only -q
.venv_logistics_service/bin/python -m pytest -q
```

Do not report the eleven check-report checks as the pytest total.

## Generated artifacts

Operational artifacts:

```text
reports/previews/tracking_events_contract_preview.json
reports/logistics_service_check_report.json
reports/logistics_service_check_report.md
reports/diagnostics/
```

These files are generated evidence and must not be staged as source changes.

Remove tracking preview:

```bash
python -c "from pathlib import Path; Path('reports/previews/tracking_events_contract_preview.json').unlink(missing_ok=True)"
```

Remove check reports:

```bash
make report-clean
```

## Escalation conditions

Stop and escalate when:

- a provider SDK, hostname, HTTP client or credential appears;
- SQLite or another production persistence implementation appears;
- provider polling, scheduler, queue or worker code appears;
- Telegram API or Telegram repository code appears;
- a safety flag changes from its required value;
- raw provider fields or responses cross the public boundary;
- event or notification replay identity becomes unstable;
- a duplicate or out-of-order observation emits a new event;
- a terminal state accepts a newer lifecycle event;
- generated reports become staged;
- a required command returns non-zero.

## Confirmed non-goals

The runbook does not authorize:

- real tracking requests;
- shipment or TTN creation;
- provider-side mutation;
- Telegram delivery;
- production event persistence;
- cross-repository writes.
