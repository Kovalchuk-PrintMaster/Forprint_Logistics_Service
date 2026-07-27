# Provider Adapter Contract

## Authoritative boundary

Logistics Service keeps one provider-neutral adapter hierarchy:

```text
app/adapters/providers/base.py
ProviderAdapter
```

Provider-specific adapters refine this boundary. They must not create a
competing adapter base or a provider-specific public contract.

## Policy sources

Blueprint standards are referenced from the Blueprint repository and are not
copied into Logistics Service.

| Purpose | Source | Authority |
|---|---|---|
| provider-adapter local rules | `docs/architecture/adapters/provider_adapter_policy.md` | module-local specialization |
| prompt execution and reporting | `coordination/standards/governance/module_prompt_execution_and_reporting_protocol.md` | Blueprint canonical standard |
| check-report behavior | `coordination/standards/testing_and_check_report_standard.md` | Blueprint canonical standard |
| recovery and documentation gate | `coordination/standards/governance/documentation_and_recovery_gate.md` | Blueprint canonical standard |
| operator and Make workflow | `coordination/standards/make_command_standard.md` | Blueprint canonical standard |
| module Make target contract | `coordination/standards/module_make_target_contract.md` | Blueprint canonical standard |

The local provider-adapter policy specializes module operation only. It cannot
weaken Blueprint reporting, recovery, Make workflow or safety requirements.

## Preserved contract

The accepted implementation preserves:

- typed provider request and result contracts;
- deterministic provider registry and resolver;
- synthetic parcel, postal, freight and taxi/courier adapters;
- deterministic preview envelopes;
- typed provider error taxonomy;
- preview-only and dry-run behavior;
- `preview_only = true`;
- `live_write = false`;
- `provider_call_performed = false`;
- final `create_shipment()` live-write guard.

## Typed operations

The public typed boundary explicitly includes:

```text
ProviderAdapter
validate_recipient()
validate_address()
build_shipment_payload_preview()
TrackingLookupRequest
TrackingLookupResult
DeliveryQuoteLookupRequest
DeliveryQuoteLookupResult
DryRunPayloadEnvelope
ProviderErrorCode
```

Unsupported operations return the typed provider-neutral state:

```text
unsupported_capability
```

Loose provider dictionaries are not the public module boundary.

## Registry and synthetic adapters

Registry implementation:

```text
app/adapters/providers/registry.py
```

Synthetic contract fixtures:

```text
app/adapters/providers/synthetic.py
```

Synthetic adapters are local fixtures. They are not real provider
integrations.

## Deterministic preview envelope

Every provider preview records provider identity, schema version, operation,
correlation reference, normalized input, payload preview, warnings, errors and
explicit safety metadata.

Credentials, authorization data and raw provider responses must not cross the
adapter boundary.

## Error taxonomy

`ProviderErrorCode` and `ProviderError` provide safe provider-neutral errors.

Unavailable providers and invalid provider responses remain typed. A future
real transport timeout must be normalized through the same safe error
boundary, but no HTTP transport exists in this closeout.

## Live-write prohibition

The contract preserves the exact invariant:

```text
create_shipment() is final
```

`create_shipment()` is final and raises
`LiveProviderWriteDisabledError`.

No shipment, TTN, courier, taxi or provider-side mutation is implemented.

## Operations and recovery

```text
docs/operations/provider_adapter_contract_runbook.md
docs/operations/provider_adapter_contract_recovery.md
```

Reporting-specific recovery remains separate:

```text
docs/operations/check_reporting_recovery.md
```

## Module validation gate

```make
module-validate:
	$(MAKE) check-report-full
	$(MAKE) governance-check
	$(MAKE) report-clean
	$(MAKE) status-report
```

The target composes existing targets only, does not invoke itself and does not
enable external writes.

## Deferred work

The following requires a new Blueprint-approved prompt:

- real provider credentials;
- provider SDK or HTTP transport;
- real tracking or quote integrations;
- provider-specific transport timeout mapping;
- live shipment or TTN creation;
- courier or taxi booking;
- automatic provider selection;
- final customer delivery price calculation;
- production database, queue or worker integration.
