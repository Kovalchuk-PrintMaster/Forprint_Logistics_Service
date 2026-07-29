# Notification Handoff Boundary

## Purpose

This boundary defines the channel-neutral notification projection produced by
ForPrint Logistics Service from an accepted tracking event.

The projection is a safe handoff contract. It is not a Telegram message, not a
delivery attempt and not a production outbox implementation.

## Producer and future consumer

Producer:

```text
ForPrint Logistics Service
```

Potential future consumers:

```text
ForPrint Telegram Bot
ForPrint CRM
ForPrint Website
```

No consumer repository is changed by this prompt.

## Authoritative model

```text
app/domain/events.py::LogisticsNotificationProjection
```

Projection creation:

```text
LogisticsNotificationProjection.from_event()
```

Source event:

```text
app/domain/tracking.py::ShipmentEventEnvelope
```

## Projection fields

The handoff includes:

- stable `notification_key`;
- canonical `notification_type`;
- explicit `projection_version`;
- source `event_id`;
- canonical `event_type`;
- source `event_version`;
- shipment reference;
- optional tracking reference;
- optional provider reference;
- timezone-aware `occurred_at`;
- optional recipient reference hint;
- safe rendering facts;
- priority;
- correlation ID;
- deterministic notification idempotency key;
- explicit safety flags.

Current projection version:

```text
logistics_notification_projection_v0_1
```

## Priority mapping

| Event | Priority |
|---|---|
| `shipment_created` | `normal` |
| `tracking_updated` | `normal` |
| `arrived` | `normal` |
| `delivered` | `normal` |
| `failed` | `critical` |
| `needs_attention` | `attention` |

Priority is a provider-neutral attention hint. It is not a channel delivery
policy.

## Safe rendering facts

Facts may contain provider-neutral values such as:

```text
current_state
event_type
provider_event_code
provider_status
safe synthetic metadata
```

Facts must not contain:

```text
telegram_message
telegram_chat
telegram_buttons
credential
password
secret
token
raw_response
```

The projection exposes data required for a future consumer to render its own
localized message.

## Telegram ownership boundary

Logistics Service does not own:

- final Telegram wording;
- localization;
- chat state;
- user sessions;
- inline buttons;
- retry rules;
- send attempts;
- delivery receipts;
- Telegram credentials;
- Telegram API transport.

Those concerns remain in the Telegram Bot module or a later Blueprint-approved
handoff/outbox step.

## Recipient hint boundary

`recipient_reference` is optional and non-canonical.

It may help a future channel module route a preview or handoff, but it does not
make Logistics Service the canonical owner of client, account or communication
identity.

No phone number, Telegram chat ID or real customer record is required by this
contract.

## Idempotency and replay

Notification identity is derived from:

- notification projection version;
- source event ID;
- optional recipient reference hint.

Notification idempotency is derived from:

- source event idempotency key;
- optional recipient reference hint;
- notification projection version.

Rebuilding a projection from the same accepted event produces the same
notification key, idempotency key and deterministic JSON.

Duplicate, out-of-order, invalid-transition and terminal-state decisions do
not emit a new notification projection.

## Serialization

```text
LogisticsNotificationProjection.to_mapping()
LogisticsNotificationProjection.to_json()
```

The mapping is deterministic and contains no canonical channel text.

## Safety invariants

```text
preview_only = true
live_write = false
provider_call_performed = false
telegram_api_call_performed = false
cross_repository_write = false
```

## Deferred work

A later Blueprint-approved step may add:

- a persistent event outbox;
- delivery-attempt state;
- retry and recovery state;
- Telegram handoff transport;
- consumer acknowledgements;
- provider polling input.

Those additions must consume this provider-neutral contract without moving
Telegram runtime ownership into Logistics Service.
