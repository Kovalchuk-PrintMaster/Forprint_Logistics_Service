# Test Address Book Boundary

## Purpose

The Logistics Service test address book provides local logistics
references for recipient lookup, aliases, shipment-time address
snapshots and preview-only shipment draft workflows.

It is a local operational logistics helper.

It is not a canonical client database, account database, order
database or canonical address registry.

## Owned local representation

Logistics Service may locally represent:

- non-canonical address book entries;
- non-canonical recipient references;
- generic or synthetic aliases;
- safe search tokens;
- city and area lookup hints;
- shipment-time address snapshots;
- preview-only shipment drafts.

Each committed entry must retain:

```yaml
non_canonical: true
logistics_reference_only: true
synthetic_data: true
real_customer_data: false
```

## Aliases are not client identity

An alias such as `офіс`, `склад` or `тестовий отримувач` is only a
local lookup hint.

An alias:

- does not establish client identity;
- does not create a client account;
- does not prove ownership of an address;
- does not replace a canonical client reference;
- may be changed without changing canonical business data.

## Address snapshots

An address selected from the local address book becomes an
`AddressSnapshot` for a particular shipment draft.

The snapshot:

- is copied at shipment-preview time;
- remains marked as a shipment-time snapshot;
- does not become canonical address truth;
- does not update CRM, Website, Telegram Bot or another module;
- does not trigger a provider API call.

## Future consumers

Future Telegram Bot, CRM and Website workflows may refer to an address
book entry by a non-canonical logistics reference.

Those consumers must not treat the entry as canonical client truth.
Cross-module use remains subject to approved Blueprint contracts.

## Local owner-maintained recipient data

Real frequent recipients may later be maintained only in the local,
Git-ignored file:

```text
runtime/address_book/owner_recipients.yaml
```

This file:

- must never be committed;
- must not contain provider credentials;
- must not be copied into Blueprint coordination records;
- must not become a canonical client database;
- must remain under owner-controlled local access;
- must not enable live provider writes.

No real recipient data is committed by this checkpoint.

## Live-write boundary

Address-book lookup may produce only a preview-only shipment draft.

The required execution state remains:

```yaml
preview_only: true
live_provider_write: false
provider_call_performed: false
```

Shipment creation, TTN creation and all other provider-side mutations
remain disabled.
