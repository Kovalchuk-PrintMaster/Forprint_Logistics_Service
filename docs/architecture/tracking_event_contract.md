# Tracking Event Contract

## Purpose

This document defines the authoritative provider-neutral tracking event
contract for ForPrint Logistics Service.

The contract records safe shipment lifecycle observations, normalizes them
into versioned Logistics events and derives channel-neutral notification
projections. It does not implement provider polling, production persistence,
Telegram delivery or cross-repository writes.

## Authoritative implementation

```text
app/domain/tracking.py
app/domain/events.py
app/services/tracking_contract_service.py
```

Compatibility models retained from the accepted local model:

```text
app/domain/tracking.py::TrackingEvent
app/domain/events.py::LogisticsNotificationEvent
```

New cross-module handoffs use:

```text
ShipmentEventEnvelope
LogisticsNotificationProjection
```

The legacy local records remain available for accepted tests and local-model
preview workflows. They are not a second canonical tracking hierarchy.

## Policy sources

Blueprint standards are referenced from the Blueprint repository and are not
copied into Logistics Service.

| Purpose | Source | Authority |
|---|---|---|
| prompt execution and reporting | `coordination/standards/governance/module_prompt_execution_and_reporting_protocol.md` | Blueprint canonical standard |
| development sequencing | `coordination/standards/governance/module_development_roadmap_policy.md` | Blueprint canonical standard |
| test and report evidence | `coordination/standards/testing_and_check_report_standard.md` | Blueprint canonical standard |
| operator workflow | `coordination/standards/make_command_standard.md` | Blueprint canonical standard |
| Make target contract | `coordination/standards/module_make_target_contract.md` | Blueprint canonical standard |
| interface presentation | `coordination/standards/visual_interface/index.yaml` | Blueprint canonical index |

Local documentation may specialize these standards but cannot weaken their
safety, evidence or repository-ownership requirements.

## Canonical event taxonomy

The contract exposes exactly six canonical provider-neutral event types:

```text
shipment_created
tracking_updated
arrived
delivered
failed
needs_attention
```

Provider-specific codes and descriptions are normalized into this taxonomy.
Unknown safe provider statuses become `needs_attention` and carry a warning
rather than creating an unversioned provider-specific public event type.

## Event version

Current schema version:

```text
tracking_event_v0_1
```

Every `ShipmentEventEnvelope` includes an explicit `event_version`.
Unsupported versions are rejected.

## Event envelope

The typed envelope includes:

- stable `event_id`;
- canonical `event_type`;
- explicit `event_version`;
- timezone-aware `occurred_at`;
- optional timezone-aware `recorded_at`;
- shipment reference;
- optional tracking reference;
- optional provider reference;
- optional safe provider event code;
- optional previous state;
- current state;
- correlation ID;
- optional causation ID;
- deterministic idempotency key;
- source;
- safe details;
- safe summary;
- warnings;
- explicit safety flags.

Unknown raw provider fields, credentials and raw provider responses must not
appear at the public top level or inside safe details.

## Lifecycle states

The event contract uses the existing authoritative `ShipmentStatus` enum.

Event projections use the following normalized states:

| Event | Current state |
|---|---|
| `shipment_created` | `draft_created` |
| `tracking_updated` | `tracking_updated` |
| `arrived` | `arrived` |
| `delivered` | `delivered` |
| `failed` | `failed` |
| `needs_attention` | `needs_attention` |

Terminal states are:

```text
delivered
failed
cancelled
```

A newer observation after a terminal event is rejected with a
`terminal_state` decision.

## Transition rules

The pure `TrackingContractService` evaluates the latest accepted event for the
same shipment reference.

Possible processing decisions:

```text
accepted
duplicate
out_of_order
invalid_transition
terminal_state
```

Important behavior:

- the same logical observation produces the same event ID and idempotency key;
- replaying an accepted observation returns `duplicate`;
- an observation not newer than the latest accepted event returns
  `out_of_order`;
- a disallowed lifecycle movement returns `invalid_transition`;
- an event after a terminal state returns `terminal_state`;
- rejected observations emit no new event and no new notification projection;
- a newer repeated `tracking_updated` observation is allowed.

## Correlation and causation

`correlation_id` groups one logical workflow or request chain.

`causation_id` identifies the prior accepted event that caused the next
transition. The service derives it from the latest accepted event when the
caller does not supply an explicit safe causation reference.

Neither field grants ownership of canonical order, client, payment or
accounting data.

## Deterministic identity and serialization

Event identity is derived from:

- event schema version;
- canonical event type;
- deterministic provider-observation fingerprint.

The fingerprint uses safe provider-neutral references, the normalized
observation time, safe provider status/code and sorted safe metadata.

`ShipmentEventEnvelope.to_json()` sorts mapping keys and uses normalized safe
pairs so the same logical event serializes identically.

## Synthetic fixtures

Authoritative synthetic fixture:

```text
examples/fixtures/tracking_events/synthetic_tracking_events.yaml
```

The fixture covers:

- successful shipment lifecycle;
- duplicate replay;
- out-of-order observation;
- arrival and delivery;
- provider failure;
- unknown provider status normalized to human attention.

The fixture contains no real customer data, credentials or provider response
payloads.

## Preview and validation

```bash
make tracking-events-check
make tracking-events-preview
```

Implementation:

```text
scripts/validation/check_tracking_events_contract.py
scripts/previews/preview_tracking_events_contract.py
```

Generated preview:

```text
reports/previews/tracking_events_contract_preview.json
```

Generated reports are operational evidence only and are not source files.

## Safety invariants

Every event, observation and notification projection preserves:

```text
preview_only = true
live_write = false
provider_call_performed = false
telegram_api_call_performed = false
cross_repository_write = false
```

## Explicitly excluded

This contract does not add:

- SQLite or another production database;
- event outbox persistence;
- provider polling or scheduling;
- provider HTTP or SDK integrations;
- production queues or workers;
- Telegram API calls;
- Telegram wording, buttons or chat state;
- canonical client, order, payment or accounting ownership;
- cross-repository writes;
- live shipment, TTN, courier or taxi creation.
