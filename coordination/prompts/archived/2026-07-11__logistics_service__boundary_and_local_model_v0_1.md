# Prompt: Logistics Service Boundary and Local Model Foundation v0.1

## Target module

`logistics_service`

## Prompt ID

`logistics_service_boundary_and_local_model_v0_1`

## Purpose

Formalize the provider-neutral local Logistics Service model after the bootstrap checkpoint.

The goal is to turn the initial skeleton into a clear local domain foundation for providers, recipients, shipment drafts, tracking requests, tracking events and logistics notification events.

This checkpoint must remain local, provider-neutral and preview-only.

Do not add live provider API integration.

Do not create real shipments.

Do not create TTNs.

Do not add real provider credentials.

## Current context

Logistics Service has completed and Blueprint is accepting:

- `logistics_service_bootstrap_and_coordination_foundation_v0_1`

Known module completion evidence:

```text
Implementation commit: 2544a71e0220c87b0be7a0be8c3f829b2d09c7ed
Completion commit: 4c5b06c
Completion report: coordination/reports/completion/logistics_service_bootstrap_and_coordination_foundation_v0_1_completion.md
Completion packet: coordination/completion_packets/records/2026-07-11__logistics_service__bootstrap_and_coordination_foundation_v0_1_completion.yaml
Tests: 19 passed
Check report: OK
Governance check: passed
Coordination metadata: 0 errors, 0 warnings
```

## The bootstrap created:

provider-neutral domain models;
preview-only provider adapter boundary;
synthetic non-canonical recipient fixtures;
documentation;
tests;
Make-first checks;
completion packet automation.

## Known non-blocking warnings:

module policy file is not available yet;
module directive index is not available yet.

These warnings are acceptable for this checkpoint unless they become check failures.

## Repository

Expected working directory:

/srv/software_development/forprint-project/forprint_logistics_service

Do not write into the Blueprint repository from the module side.

Strategic boundary

Logistics Service may own:

logistics provider references;
provider capability metadata;
logistics recipient references;
shipment-time address snapshots;
shipment drafts;
shipment payload previews;
tracking requests;
tracking events;
logistics notification events;
local preview/audit data for logistics workflows.

Logistics Service must not own:

canonical clients;
canonical orders;
product catalog;
material catalog;
price calculation;
accounting truth;
payment truth;
warehouse stock truth;
production task ownership;
Telegram conversation state;
Website session state.
Safety policy

This checkpoint must not perform live provider writes.

## Do not implement:

real Nova Poshta TTN creation;
real Ukrposhta shipment creation;
real SAT shipment creation;
real Meest shipment creation;
real Uklon/Bolt/Uber order creation;
automatic courier/taxi calls;
live provider write of any kind;
production API;
1C write;
payment write;
stock mutation;
canonical order creation;
canonical client database.

All live-write capabilities must remain disabled by default.

Required implementation

Build a local model foundation around the existing bootstrap artifacts.

Inspect current files before changing them.

Likely files to inspect or update:

app/domain/providers.py
app/domain/recipients.py
app/domain/shipments.py
app/domain/tracking.py
app/domain/events.py
app/adapters/providers/base.py
app/storage/
app/services/
examples/fixtures/recipients/test_recipients.yaml
tests/
docs/
scripts/
Makefile

The assistant may add small focused modules if useful, for example:

app/storage/repositories.py
app/storage/in_memory.py
app/services/shipment_draft_service.py
app/services/tracking_event_service.py
scripts/previews/preview_local_logistics_model.py
examples/workflows/shipment_draft_preview.yaml
examples/workflows/tracking_event_preview.yaml

## Keep the structure simple.

Do not add a production database.

Do not add FastAPI.

Do not add systemd.

Do not add provider SDKs.

Required local model behavior

Implement or confirm local model support for:

Logistics provider references

Provider records should describe provider identity and capability metadata without credentials.

Recipient references

Recipient records must remain non-canonical logistics references, not canonical client records.

Address snapshots

Address data should be shipment-time snapshots, not canonical address ownership.

Shipment drafts

Shipment drafts should represent local preview data only.

## A shipment draft may include:

draft id;
provider ref;
recipient ref;
address snapshot;
cargo/package description;
status;
created/updated timestamps or simple metadata;
dry-run / preview-only marker.

## Tracking requests

Tracking requests should represent a local request to track a provider reference in future.

They must not call provider APIs in this checkpoint.

Tracking events

Tracking events should be provider-neutral and local.

## Suggested statuses:

draft_created
tracking_requested
tracking_updated
arrived
delivered
failed
needs_attention

Logistics notification events

Notification events should be local payloads that Telegram Bot, CRM or Website may later display.

Do not implement real Telegram/CRM/Website delivery.

Required repository boundary

Add a local repository interface and at least one safe local implementation.

## Recommended:

app/storage/repositories.py
app/storage/in_memory.py

The repository may support:

save/get/list providers;
save/get/list recipients;
save/get/list shipment drafts;
save/get/list tracking events;
save/get/list notification events.

This must be in-memory or fixture-based only unless there is an explicit reason for simple local file examples.

Do not add production database ownership.

Do not add SQLite unless the prompt implementation can keep it clearly local, non-production and justified. Prefer in-memory for this checkpoint.

Required examples

Add local examples that show the model without calling providers.

## Recommended examples:

examples/workflows/shipment_draft_preview.yaml
examples/workflows/tracking_request_preview.yaml
examples/workflows/notification_event_preview.yaml

Examples must clearly state:

non_canonical: true
preview_only: true
live_provider_write: false
Required preview

Add a human-readable preview command if practical.

## Recommended target:

make logistics-model-preview

or a script:

scripts/previews/preview_local_logistics_model.py

## The preview should show:

Provider: Nova Poshta / local example provider
Recipient: synthetic non-canonical recipient
Shipment draft: preview-only
Tracking: local event sequence preview
Notification: local notification event preview
Live provider write: disabled
Required docs

## Add or update documentation:

docs/architecture/local_model_foundation.md
docs/architecture/boundaries/logistics_service_boundary.md
docs/development/testing/local_test_data_policy.md
docs/architecture/adapters/provider_adapter_policy.md

## Docs must explain:

what Logistics Service owns;
what it does not own;
how shipment drafts differ from canonical orders;
how recipient references differ from canonical clients;
how address snapshots differ from canonical addresses;
why live provider writes remain disabled;
how future Telegram Bot / CRM / Website consumers should treat logistics events.
Required Makefile/check-report visibility

Expose the new validation or preview through the make-first workflow where practical.

Do not rewrite the Makefile broadly.

## Recommended new or updated targets:

make logistics-model-preview
make logistics-check
make check-report

The check report should include visibility for local model validation if a new validator or preview is added.

## Required tests

Add or update tests for:

provider records and capability metadata;
recipient references are non-canonical;
address snapshots are shipment-time snapshots;
shipment draft creation is preview-only;
tracking request does not call providers;
tracking events are local provider-neutral records;
notification events are local display payloads;
repository save/get/list behavior;
live provider writes remain disabled;
examples validate;
no secrets are introduced;
no forbidden ownership fields are introduced.

## Run:

make governance-check
make check
make check-report
git diff --check
git status --short
Required completion and reporting workflow

At the end of this task, prepare a module-side completion packet inside the Logistics Service repository.

Use the completion packet automation if available.

Required module-side files:

coordination/reports/completion/<prompt_id>_completion.md
coordination/reports/index.yaml
coordination/status/current_status.yaml
coordination/status/current_status.md
coordination/status/next_questions_for_blueprint.md
coordination/completion_packets/records/<record>.yaml

## Required completion report content:

prompt id;
branch;
implementation commit;
completion commit;
summary of implemented work;
files changed;
checks passed;
known warnings;
explicit no-live-provider-write confirmation;
explicit secrets policy confirmation;
explicit boundary confirmation;
confirmation that no Blueprint files were written directly;
open questions for Blueprint, or explicit “No open questions”.

## Status/report formatting requirements:

keep current_status.yaml valid YAML;
keep current_status.md readable Markdown;
close all Markdown code fences;
keep only current open questions in next_questions_for_blueprint.md;
ensure all text files end with a newline.
Blueprint reporting boundary

## Logistics Service may read Blueprint prompts and standards.

Logistics Service must not write directly into:

/srv/software_development/forprint-project/forprint_system_blueprint/

Blueprint-side incoming report registration and Blueprint review are separate Blueprint-owned actions.

Explicit non-goals

## Do not implement:

live Nova Poshta API integration;
live Nova Poshta TTN creation;
live Ukrposhta/SAT/Meest writes;
live Uklon/Bolt/Uber order creation;
automatic courier/taxi calls;
production daemon/service;
systemd unit;
real provider credentials;
canonical client database;
canonical order database;
product catalog;
price calculation;
payment status changes;
warehouse stock reservation;
1C integration;
Telegram Bot code changes;
Website code changes;
CRM code changes;
Calculator code changes;
Integration Gateway writes;
production database.
Definition of done

## This prompt is complete when:

local provider-neutral model foundation exists;
local repository interface and implementation exist;
shipment draft preview flow exists;
tracking event preview flow exists;
notification event preview flow exists;
examples exist and validate;
tests are green;
check report is green;
live provider writes remain disabled;
no real credentials are committed;
no forbidden ownership is added;
completion packet is created inside Logistics Service repo;
final module commit hash is reported back to Blueprint.

---
