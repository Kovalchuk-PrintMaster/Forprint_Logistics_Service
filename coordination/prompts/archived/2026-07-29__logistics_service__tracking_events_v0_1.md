# Logistics Service Tracking Events and Notification Contracts v0.1

## Prompt metadata

```yaml
prompt_id: logistics_service_tracking_events_v0_1
sequence: 5
target_module: logistics_service
phase: tracking_events_v0_1
priority: critical
source_module: forprint_system_blueprint
status: approved
created_at: '2026-07-29'
```

## Purpose

Create the provider-neutral shipment event contract that will connect Logistics Service with Telegram Bot and future channels without coupling the modules to Nova Poshta, Ukrposhta, taxi providers, a temporary local database or the future central database.

This prompt establishes the common event language before provider-specific integrations and local persistence are expanded.

The result must allow Logistics Service to produce deterministic shipment lifecycle events and safe notification payload previews while keeping shipment truth inside Logistics Service and presentation/conversation ownership inside Telegram Bot.

## Accepted foundation

This prompt continues accepted Logistics work:

```text
logistics_service_bootstrap_and_coordination_foundation_v0_1
logistics_service_boundary_and_local_model_v0_1
logistics_service_test_address_book_v0_1
logistics_service_provider_adapter_contract_v0_1
```

Provider Adapter Contract v0.1 was accepted by Blueprint from completion commit:

```text
4812047963427043d616871075ac807a35e51aff
```

Blueprint review evidence:

```text
coordination/review_packets/logistics_service/processed/
2026-07-29__logistics_service_provider_adapter_contract_v0_1__accepted.yaml
```

## Required reading before implementation

Read the current Blueprint copies through the approved Blueprint pull and prompt-navigation workflow.

Required sources:

```text
coordination/outgoing_prompts/logistics_service/index.yaml
coordination/roadmaps/logistics_service.yaml
coordination/standards/governance/module_prompt_execution_and_reporting_protocol.md
coordination/standards/governance/module_development_roadmap_policy.md
coordination/standards/testing_and_check_report_standard.md
coordination/standards/make_command_standard.md
coordination/standards/module_make_target_contract.md
coordination/standards/visual_interface/index.yaml
```

Read the accepted provider contract, runbook and recovery evidence already present in the Logistics repository.

At minimum review existing equivalents of:

```text
app/domain/shipments.py
app/domain/tracking.py
app/domain/providers.py
app/adapters/providers/base.py
docs/architecture/provider_adapter_contract.md
docs/operations/provider_adapter_contract_runbook.md
docs/operations/provider_adapter_contract_recovery.md
```

Use existing authoritative files when their actual paths differ. Do not create duplicate domain hierarchies.

## Required Git workflow

Start from the accepted Logistics feature state or the current clean default branch after that state has been integrated according to the repository's normal policy.

Create a dedicated feature branch:

```text
feature/logistics-tracking-events-contract-v01
```

Before implementation report:

```text
current branch;
base commit;
working-tree status;
resolved Blueprint prompt id;
resolved roadmap step.
```

Do not merge, delete or rename the feature branch during this task.

## Ownership boundaries

### Logistics Service owns

```text
shipment lifecycle semantics;
provider-neutral tracking events;
event normalization;
event versioning;
event ordering expectations;
correlation and idempotency metadata;
notification-ready logistics facts;
safe payload previews;
local Logistics tests and fixtures.
```

### Telegram Bot owns

```text
conversation state;
message wording and localization;
buttons and interaction flows;
recipient/channel preferences;
Telegram delivery attempts;
Telegram-specific retry behavior;
Telegram runtime persistence.
```

### Future central data platform owns

```text
canonical cross-module persistence;
canonical order and client records;
shared database infrastructure;
cross-module transaction policy.
```

Logistics must not directly write into Telegram Bot or another repository.

Telegram Bot must not become the canonical owner of shipment state.

The temporary local Logistics database is not canonical ecosystem truth. Database implementation belongs to the next roadmap step and is outside this prompt.

## Main implementation scope

### 1. Canonical provider-neutral event taxonomy

Define one authoritative Logistics event taxonomy.

The initial required events are:

```text
shipment_created
tracking_updated
arrived
delivered
failed
needs_attention
```

Clarify the semantic meaning and minimum triggering conditions for every event.

Recommended interpretation:

```text
shipment_created
    A shipment draft or accepted shipment representation entered the Logistics
    lifecycle. This does not imply that a real provider write occurred.

tracking_updated
    A newer normalized provider or synthetic tracking state was accepted.

arrived
    The shipment arrived at the expected pickup, terminal or destination point,
    but has not necessarily been handed to the final recipient.

delivered
    Delivery to the final recipient was confirmed by normalized evidence.

failed
    The current delivery workflow cannot continue automatically because of a
    terminal or operational failure.

needs_attention
    Human review is required, but the workflow is not necessarily terminal.
```

Do not encode provider names into canonical event types.

Provider-specific raw statuses may be preserved as safe metadata but must be normalized before they cross the public Logistics boundary.

### 2. Typed event envelope

Create or refine a typed, versioned event envelope.

At minimum it must represent:

```text
event_id;
event_type;
event_version;
occurred_at;
recorded_at when needed;
shipment_id or shipment_reference;
tracking_reference when available;
provider_id when available;
provider_event_code when safe;
previous_state when available;
current_state;
correlation_id;
causation_id when available;
idempotency_key;
source;
preview_only;
live_write;
payload or details;
safe human-readable summary;
warnings;
```

Required invariants:

```text
event_id is stable and unique within the defined boundary;
event_type is restricted to the canonical taxonomy;
event_version is explicit;
occurred_at is timezone-aware;
preview_only is explicit;
live_write is always false in this prompt;
idempotency_key is deterministic for the same logical input;
unknown provider fields do not leak into the canonical top level;
secrets and raw credentials are never serialized;
the envelope can be serialized deterministically.
```

Do not expose loosely structured dictionaries as the only public contract when typed models are practical.

### 3. Shipment lifecycle and transition rules

Define a small provider-neutral lifecycle model sufficient to validate the required events.

The lifecycle may include states such as:

```text
draft
created
in_transit
arrived
delivered
failed
needs_attention
```

Use the existing Logistics shipment/tracking model when possible.

Document and test allowed transitions.

At minimum address:

```text
creation of an initial shipment lifecycle event;
repeated tracking updates;
transition to arrived;
transition from arrived to delivered;
failure handling;
needs-attention handling;
duplicate event handling;
out-of-order event handling;
terminal-state behavior;
provider status normalization.
```

Do not build a production workflow engine or background worker.

### 4. Notification projection contract

Create a provider-neutral notification projection derived from a Logistics event.

The projection is the handoff surface for Telegram Bot and future channels.

At minimum it should contain:

```text
notification_id or stable notification key;
notification_type;
event_id;
event_type;
event_version;
shipment_reference;
tracking_reference when available;
provider_id when available;
occurred_at;
recipient_reference or channel-recipient hint when available;
safe facts required for message rendering;
priority or attention level;
correlation_id;
idempotency_key;
preview_only;
```

The notification projection must not contain:

```text
Telegram message text as the canonical source;
Telegram chat state;
Telegram buttons;
provider credentials;
raw sensitive provider responses;
canonical client data;
canonical order data;
database connection details.
```

Provide examples showing how Telegram Bot can consume the contract while remaining responsible for channel-specific rendering.

### 5. Correlation, causation and idempotency

Define deterministic rules for:

```text
event correlation;
event causation;
logical duplicate detection;
notification duplicate detection;
replay safety;
same-status repeated provider snapshots;
out-of-order provider observations;
event version compatibility.
```

Tests must prove that repeated processing of the same logical input does not produce conflicting event identities or duplicate notification projections.

Do not add a production message broker, queue or scheduler.

### 6. Synthetic event and notification fixtures

Add safe synthetic fixtures covering at least:

```text
shipment creation preview;
one or more tracking updates;
arrival;
delivery;
provider failure;
manual-attention case;
duplicate provider update;
out-of-order provider update;
notification projection for Telegram;
notification replay/idempotency.
```

Use synthetic identifiers and addresses.

Do not include real customer data, real phone numbers, real credentials or live provider payloads.

### 7. Preview and operator workflow

Add a Make-first read-only preview or extend an existing safe preview workflow.

The preview should demonstrate:

```text
canonical event taxonomy;
event envelope;
lifecycle transition;
normalized provider tracking update;
notification projection;
idempotency behavior;
preview_only = true;
live_write = false;
provider_call_performed = false.
```

Prefer a focused target such as:

```text
make tracking-events-check
```

or an equivalent existing naming pattern.

The target must not perform:

```text
network calls;
provider writes;
Telegram API calls;
cross-repository writes;
database migrations;
background worker startup.
```

Integrate the focused target into the module's existing validation/reporting workflow only when that remains read-only, deterministic and non-recursive.

### 8. Architecture, runbook and recovery documentation

Add or update documentation for:

```text
tracking event taxonomy;
typed event envelope;
lifecycle states and transitions;
provider status normalization;
notification projection;
Telegram ownership boundary;
idempotency and replay behavior;
preview workflow;
recovery from incompatible event or notification contracts;
future local persistence adapter boundary;
future central database migration boundary.
```

Recommended locations:

```text
docs/architecture/tracking_event_contract.md
docs/architecture/boundaries/notification_handoff_boundary.md
docs/operations/tracking_events_runbook.md
docs/operations/tracking_events_recovery.md
```

Use existing equivalent files instead of creating duplicates.

The recovery guide must explain a file-scoped rollback to the last accepted event contract and the checks required after recovery.

## Local persistence boundary

Do not implement the SQLite persistence roadmap step in this prompt.

It is allowed to define serialization contracts or repository-neutral interfaces needed to keep the event model persistence-ready.

It is not allowed to add:

```text
production database migrations;
canonical customer/order tables;
cross-module database ownership;
hidden direct SQL dependencies in domain models;
database-specific fields in the public event envelope.
```

Any small test-only in-memory store must be clearly classified as a fixture, not as the local persistence implementation.

## Telegram coordination boundary

This prompt prepares a contract for Telegram Bot but does not modify Telegram Bot.

Required handoff evidence:

```text
one canonical notification projection schema;
sample payloads for every required event type;
field ownership table;
required/optional field table;
version compatibility rule;
idempotency rule;
error and unsupported-version behavior;
explicit no-cross-repository-write confirmation.
```

Record any question that requires Telegram-side agreement in:

```text
coordination/status/next_questions_for_blueprint.md
```

Do not block provider-neutral event implementation on message wording or Telegram UI choices.

## Required tests

Add or update tests for:

```text
all required event types;
typed envelope validation;
timezone-aware timestamps;
event-version validation;
deterministic serialization;
lifecycle transition rules;
invalid transitions;
terminal-state behavior;
provider status normalization;
duplicate update handling;
out-of-order update handling;
correlation and causation metadata;
deterministic idempotency keys;
notification projection;
notification replay safety;
safe rendering;
no credentials;
no real provider calls;
no provider writes;
no Telegram calls;
no cross-repository writes;
preview command;
Make target contract;
report generation.
```

Maintain or increase the current full-suite confidence. Report exact collection and exact pass totals separately from check-report totals.

## Required commands

Run at minimum:

```text
make tracking-events-check
make governance-check
make coordination-check
make check
make check-report
make check-report-full
make module-validate
git diff --check
git status --short
```

When the focused target has a different accepted name, report that exact name and explain why it is canonical.

Generated reports and diagnostics must not remain staged or committed unless repository policy explicitly classifies them as tracked evidence.

## Completion workflow

Use the module-side completion packet automation.

Required module-side outputs:

```text
coordination/completion_packets/records/
coordination/reports/completion/
coordination/reports/index.yaml
coordination/status/current_status.yaml
coordination/status/current_status.md
coordination/status/next_questions_for_blueprint.md
```

The completion packet and completion report must include:

```text
prompt id;
branch;
base commit;
implementation commit;
completion commit;
changed files;
authoritative event contract path;
event taxonomy;
lifecycle transition summary;
notification projection path;
Telegram handoff examples;
idempotency rules;
focused and full test totals;
check-report totals;
warnings and blockers;
generated artifact handling;
preview_only confirmation;
live_write false confirmation;
provider_call_performed false confirmation;
Telegram API call false confirmation;
cross-repository write false confirmation;
credentials added false confirmation;
open questions or explicit no-open-questions;
push and upstream-divergence evidence.
```

The final assistant handoff must use compact tables or compact sections and link to detailed evidence rather than reproducing full logs.

## Explicit non-goals

Do not implement:

```text
local SQLite persistence and migrations;
future central database integration;
Nova Poshta live or read-only API integration;
Ukrposhta live or read-only API integration;
taxi or courier booking;
real TTN creation;
live provider tracking calls;
Telegram Bot code changes;
Telegram API calls;
Telegram message wording as canonical logistics data;
production queues;
production schedulers;
production background workers;
live shipment mutations;
provider credentials;
canonical client ownership;
canonical order ownership;
final delivery pricing;
payment/accounting writes;
warehouse mutations;
CRM changes;
Website changes;
Calculator changes;
Integration Gateway writes.
```

## Definition of done

The prompt is complete when:

```text
one provider-neutral event taxonomy is authoritative;
all six required event types are implemented and documented;
a typed versioned event envelope exists;
shipment lifecycle transitions are deterministic and tested;
provider observations normalize into canonical events;
correlation, causation and idempotency rules are explicit;
notification projections are channel-neutral and Telegram-ready;
synthetic fixtures cover normal, failure, duplicate and out-of-order cases;
a read-only Make-first preview exists;
preview_only remains true;
live_write remains false;
no real provider or Telegram calls occur;
no local or central database implementation is introduced;
architecture, runbook and recovery documentation exist;
completion automation is valid and idempotent;
full checks pass;
the feature branch is committed and pushed;
Blueprint receives complete review evidence.
```
