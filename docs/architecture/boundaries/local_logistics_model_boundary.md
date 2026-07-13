# Local Logistics Model Boundary

## Purpose

The local Logistics Service model provides a safe, provider-neutral
foundation for recipient lookup, shipment previews, tracking intent,
normalized tracking events and local notification payloads.

It does not perform live logistics operations.

## Ownership boundary

Logistics Service owns only local logistics representations:

- provider references and capability metadata;
- non-canonical recipient references;
- non-canonical address book entries;
- recipient aliases and safe lookup hints;
- shipment-time address snapshots;
- preview-only shipment drafts;
- local-only tracking requests;
- provider-neutral local tracking events;
- local notification payloads;
- process-local in-memory repository behavior.

Logistics Service does not own:

- canonical clients or client accounts;
- canonical addresses;
- canonical orders;
- product or material catalogs;
- price calculation;
- invoices, payments or accounting truth;
- warehouse stock mutation;
- 1C writes or automatic posting;
- Telegram Bot conversation state;
- CRM client truth;
- Website session state;
- provider credentials;
- production databases.

## Safety invariants

| Model | Required invariant |
|---|---|
| Address book entry | `non_canonical: true` |
| Address book entry | `logistics_reference_only: true` |
| Committed fixture | `synthetic_data: true` |
| Committed fixture | `real_customer_data: false` |
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

## Address book boundary

`AddressBookEntry` is a non-canonical local logistics reference.

Aliases and search tokens support operator lookup. They do not
establish client identity, client account ownership or canonical
address ownership.

`AddressBookService` may:

- save and list local entries;
- search by alias, display name, recipient reference or safe token;
- apply an optional city or area hint;
- create a shipment-time `AddressSnapshot`.

The resulting snapshot may be passed to `ShipmentDraftService` only
for a preview-only shipment draft.

## Repository boundary

`LogisticsRepository` defines the local storage protocol.

`InMemoryLogisticsRepository`:

- stores data only inside the current Python process;
- supports address-book save, get, list and lookup behavior;
- performs no filesystem or database writes;
- performs no provider API calls;
- validates local shipment references;
- does not claim canonical or operational database ownership.

## Local private data path

Future owner-maintained frequent-recipient data may exist only at:

```text
runtime/address_book/owner_recipients.yaml
```

The path is ignored by Git. The file is not required for tests and
must never be committed.

## Service boundary

Current local services include:

- `AddressBookService`;
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
