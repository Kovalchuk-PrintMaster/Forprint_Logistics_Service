# Provider Adapter Contract

## Authoritative boundary

Logistics Service has one provider-neutral adapter hierarchy:

```text
app/adapters/providers/base.py
ProviderAdapter
```

Provider-specific adapters must refine this boundary. They must not
introduce a competing base class or provider-specific public
contract.

## Capability discovery

Provider-neutral discovery uses:

```text
ProviderCapability
ProviderOperation
ProviderCapabilitySupport
ProviderCapabilityDescription
```

Every capability has an explicit supported or unsupported result.

Live shipment creation is always unavailable.

## Typed adapter operations

`ProviderAdapter` defines typed boundaries for:

```text
validate_recipient()
validate_address()
build_shipment_payload_preview()
track()
lookup_delivery_quote()
TrackingLookupRequest
TrackingLookupResult
```

Loose provider dictionaries are not the public service boundary.

Provider-specific preview details may exist only inside
`DryRunPayloadEnvelope`.

## Dry-run invariants

Every provider-neutral execution keeps:

```text
preview_only = true
live_write = false
provider_call_performed = false
```

Sensitive credentials, authorization values, tokens and raw
provider responses must not cross the adapter boundary.

## Delivery quote boundary

`DeliveryQuoteLookupRequest` and
`DeliveryQuoteLookupResult` reserve a read-only typed boundary for
future provider quote support.

The current base adapter returns an explicit
`unsupported_capability` result.

It does not perform a quote API call and does not calculate the
final customer price.

## Provider errors

`ProviderErrorCode` is the machine-readable provider-neutral error
taxonomy.

`ProviderError` exposes safe text, retryability and typed provider
context without exposing raw sensitive values.

## Live-write prohibition

The `ProviderAdapter` method create_shipment() is final.

It always raises `LiveProviderWriteDisabledError` with:

```text
code = live_write_disabled
retryable = false
operation = live_shipment_creation
```

No live shipment, TTN, courier, taxi or provider-side mutation is
implemented.

## Deferred work

The following remains deferred:

- provider registry or resolver;
- synthetic multi-provider fixtures;
- provider adapter preview workflow;
- real tracking or quote calls;
- provider SDK or HTTP integration;
- compact reporting alignment;
- final delivery price calculation.
