# Provider Adapter Policy

## Source of truth

Every future provider integration must implement:

```text
app/adapters/providers/base.py
ProviderAdapter
```

A provider-specific adapter must not create a parallel adapter base.

## Allowed operations

An adapter may currently:

- describe capabilities;
- report unsupported capabilities explicitly;
- validate recipient and address data through typed contracts;
- build a typed shipment payload preview;
- return typed read-only tracking information;
- return an unavailable typed delivery quote result.

## Forbidden operations

An adapter must not:

- create a TTN or waybill;
- submit a shipment;
- book a courier;
- book a taxi;
- mutate or cancel provider-side objects;
- load real production credentials into domain models;
- expose raw provider responses;
- calculate a final customer price.

## Execution safety

Provider-neutral execution requires:

```text
preview_only = true
live_write = false
provider_call_performed = false
```

`ProviderAdapter.create_shipment()` is final and always raises
`LiveProviderWriteDisabledError`.
