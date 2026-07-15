# Provider Adapter Contract

## Purpose

Logistics Service keeps one provider-neutral contract for future
parcel, postal, freight, taxi and local courier adapters.

The existing boundary under `app/adapters/providers/base.py`
remains authoritative. This contract foundation refines its typed
domain vocabulary rather than creating another adapter hierarchy.

## Capability semantics

`ProviderCapability` describes provider-neutral functionality.

`ProviderOperation` describes a requested operation.

`LogisticsProvider.capability_support()` and
`LogisticsProvider.operation_support()` always return an explicit
`ProviderCapabilitySupport` result.

Unsupported operations are represented explicitly. They are not
inferred from missing dictionary keys or provider-specific values.

`LIVE_SHIPMENT_CREATION` is always unavailable in this checkpoint.

## Typed requests and results

The provider-neutral contract includes typed models for:

- recipient validation;
- address validation;
- shipment payload preview;
- read-only tracking lookup;
- provider capability description;
- dry-run execution metadata.

Provider-specific details may exist only inside the safe payload
preview portion of `DryRunPayloadEnvelope`.

## Dry-run envelope

`DryRunPayloadEnvelope` records:

- provider ID;
- provider-neutral operation;
- schema version;
- correlation reference;
- normalized input summary;
- provider payload preview;
- validation messages;
- warnings;
- generated preview artifacts.

Its invariants require:

```text
preview_only = true
live_write = false
provider_call_performed = false
```

Sensitive payload keys such as tokens, passwords, credentials,
authorization values and raw provider responses are rejected.

## Error taxonomy

`ProviderErrorCode` defines the provider-neutral machine-readable
taxonomy.

`ProviderError` provides:

- a safe human-readable message;
- explicit retryability;
- optional provider and operation context;
- safe metadata keys;
- rendering that excludes raw metadata values.

Provider-specific errors may later be normalized into this taxonomy.
Raw sensitive responses must not cross the adapter boundary.

## Deferred adapter refinement

A later checkpoint in the same prompt will update
`ProviderAdapter` to consume and return these typed contracts.

Registry/resolver behavior, synthetic multi-provider fixtures,
preview workflow and compact reporting alignment remain separate
tested checkpoints.

## Safety boundary

This contract does not permit:

- provider HTTP or SDK calls;
- real credentials;
- real tracking calls;
- shipment or TTN creation;
- courier or taxi booking;
- provider-side writes;
- canonical client or order ownership;
- final customer price ownership.
