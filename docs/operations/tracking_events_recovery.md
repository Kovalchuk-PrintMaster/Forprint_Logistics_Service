# Tracking Events Recovery Guide

## Purpose

Recover the provider-neutral tracking event contract, synthetic fixtures,
preview workflow and Make/check-report integration without enabling an
external call or production write.

## Known implementation checkpoints

```text
accepted provider foundation:
4812047963427043d616871075ac807a35e51aff

tracking-events prompt intake:
344732b393e1b18e30b673f1777c27bd1ed57784

core tracking event contract:
61ca42ba95a62ce3a91335e273c4edf2d5d23754

synthetic fixture and preview workflow:
91d53512e2af40fcc800c44d331ff604c50cc813
```

These commits are immutable evidence points. Blueprint acceptance of the full
tracking-events prompt is recorded separately after completion review.

## Establish state

```bash
git status -sb
git branch --show-current
git rev-parse HEAD
git log -6 --oneline
```

Create a recovery branch before restoring source files:

```bash
git switch -c recovery/tracking-events-contract-v0-1
```

Do not use `git reset --hard` as the routine recovery path.

## Restore core domain and service

```bash
CORE_COMMIT="61ca42ba95a62ce3a91335e273c4edf2d5d23754"

git restore --source "$CORE_COMMIT" -- \
  app/domain/__init__.py \
  app/domain/events.py \
  app/domain/tracking.py \
  app/services/__init__.py \
  app/services/tracking_contract_service.py \
  tests/unit/domain/test_tracking_event_contract.py \
  tests/unit/services/test_tracking_contract_service.py
```

Verify:

```bash
.venv_logistics_service/bin/python -m pytest \
  -q \
  -o addopts='' \
  tests/unit/domain/test_tracking_event_contract.py \
  tests/unit/services/test_tracking_contract_service.py
```

## Restore fixture, preview and focused validation

```bash
PREVIEW_COMMIT="91d53512e2af40fcc800c44d331ff604c50cc813"

git restore --source "$PREVIEW_COMMIT" -- \
  Makefile \
  examples/fixtures/tracking_events/synthetic_tracking_events.yaml \
  scripts/diagnostics/run_logistics_checks.py \
  scripts/previews/preview_tracking_events_contract.py \
  scripts/validation/check_tracking_events_contract.py \
  tests/contract/fixtures/test_tracking_events_fixture.py \
  tests/contract/policies/test_tracking_events_make_targets.py \
  tests/integration/workflows/test_tracking_events_check_visibility.py \
  tests/integration/workflows/test_tracking_events_preview.py
```

Verify:

```bash
make tracking-events-check
make tracking-events-preview
```

## Duplicate or out-of-order regression

Inspect:

```text
app/services/tracking_contract_service.py
tests/unit/services/test_tracking_contract_service.py
examples/fixtures/tracking_events/synthetic_tracking_events.yaml
```

Required behavior:

- exact logical replay returns `duplicate`;
- older or equal non-duplicate observation returns `out_of_order`;
- neither decision emits a new notification projection.

Restore the core service and focused tests from `CORE_COMMIT` when this
behavior changes unexpectedly.

## Event identity regression

Inspect:

```text
app/domain/tracking.py::ProviderTrackingObservation.logical_fingerprint
app/services/tracking_contract_service.py::_identity
app/domain/tracking.py::ShipmentEventEnvelope.to_json
```

Required behavior:

- safe metadata is sorted;
- identical logical observations produce identical fingerprints;
- event ID and event idempotency key are stable;
- serialization is deterministic.

## Notification replay regression

Inspect:

```text
app/domain/events.py::LogisticsNotificationProjection.from_event
app/domain/events.py::LogisticsNotificationProjection.to_json
```

Required behavior:

- same accepted event and recipient hint produce the same notification key;
- same source idempotency and recipient hint produce the same notification
  idempotency key;
- no canonical Telegram message, buttons or chat state are emitted.

## Unsafe execution flag

Treat any unsafe flag as an immediate stop condition.

Required values:

```text
preview_only = true
live_write = false
provider_call_performed = false
telegram_api_call_performed = false
cross_repository_write = false
```

Do not run provider, Telegram or production-storage commands.

## Sensitive fixture or payload finding

Inspect:

```text
examples/fixtures/tracking_events/synthetic_tracking_events.yaml
scripts/previews/preview_tracking_events_contract.py
app/domain/tracking.py
app/domain/events.py
```

Remove credentials, phone numbers, raw provider responses and unknown
provider-specific fields from the public contract.

Verify:

```bash
make tracking-events-check
```

## Make/check-report regression

Required targets:

```text
tracking-events-check
tracking-events-preview
```

Required check-report entry:

```text
Tracking events
```

Verify:

```bash
make tracking-events-check
make check-report
make check-report-full
```

Expected check-report inventory:

```text
11 total
11 passed
0 warning
0 failed
```

## Full verification after recovery

```bash
make tracking-events-check
make check
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

## Generated artifact cleanup

```bash
python -c "from pathlib import Path; Path('reports/previews/tracking_events_contract_preview.json').unlink(missing_ok=True)"
make report-clean
```

Generated preview and check-report files must not be staged.

## Confirm no external action occurred

Confirm:

- no provider SDK or HTTP client was added;
- no provider credential or endpoint was configured;
- no provider call occurred;
- no Telegram API call occurred;
- no production database, queue, worker or scheduler was introduced;
- no cross-repository write occurred;
- no shipment, TTN, courier or taxi object was created.
