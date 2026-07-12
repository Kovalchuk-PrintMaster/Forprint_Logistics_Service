# Local Logistics Model Boundary

## Purpose

The local Logistics Service model provides a safe,
provider-neutral foundation for shipment previews,
tracking intent, normalized tracking events and future
notification payloads.

It does not perform live logistics operations.

## Ownership boundary

Logistics Service owns only local logistics representations:

- provider references and capability metadata;
- non-canonical recipient references;
- shipment-time address snapshots;
- preview-only shipment drafts;
- local-only tracking requests;
- provider-neutral local tracking events;
- local notification payloads;
- process-local in-memory repository behavior.

Logistics Service does not own:

- canonical client or account data;
- canonical orders;
- product or material catalogs;
- price calculation;
- invoices, payments or accounting truth;
- warehouse stock mutation;
- 1C writes or automatic posting;
- Telegram Bot, Website or CRM delivery;
- provider credentials;
- production databases.

## Safety invariants

The current checkpoint requires all of the following:

| Model | Required invariant |
|---|---|
| Recipient reference | `non_canonical: true` |
| Address | `shipment_time_snapshot: true` |
| Shipment draft | `preview_only: true` |
| Shipment draft | `live_provider_write: false` |
| Tracking request | `local_only: true` |
| Tracking request | `provider_call_performed: false` |
| Tracking event | `local_record: true` |
| Notification event | `local_payload: true` |
| Notification event | `delivery_performed: false` |

Domain models reject unsafe alternatives during construction.

## Repository boundary

`LogisticsRepository` defines the local storage protocol.

`InMemoryLogisticsRepository` is the only implementation
introduced by this checkpoint. It:

- stores data only inside the current Python process;
- performs no filesystem or database writes;
- performs no provider API calls;
- validates local shipment references;
- does not claim canonical or operational database ownership.

## Service boundary

The local services create and store safe model records:

- `ShipmentDraftService`;
- `TrackingEventService`;
- `NotificationEventService`.

These services do not import provider adapters, HTTP clients,
database clients or API frameworks.

## Deferred work

The following remains explicitly deferred:

- provider SDKs;
- live shipment or TTN creation;
- provider-side tracking calls;
- courier or taxi integrations;
- production API;
- production persistence;
- real credentials;
- automatic notification delivery.
