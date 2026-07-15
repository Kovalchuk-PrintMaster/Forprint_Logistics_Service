# Provider Contract Fixtures

## Purpose

Logistics Service includes four provider-neutral synthetic adapter
fixtures:

```text
synthetic_parcel
synthetic_postal
synthetic_freight
synthetic_taxi_courier
```

They validate the common `ProviderAdapter` contract without using
provider SDKs, HTTP clients, credentials or real customer data.

## Provider classes

The fixtures cover:

- a Nova Poshta-like parcel workflow;
- a Ukrposhta-like postal workflow;
- a generic freight workflow;
- a generic taxi/courier workflow.

These names describe contract behavior only. They are not real
provider integrations.

## Capabilities

Parcel, postal and freight fixtures expose read-only tracking as a
supported contract capability.

The taxi/courier fixture intentionally does not expose tracking.
Its tracking lookup returns a typed `unsupported_capability` error.

Delivery quote lookup remains unavailable for every fixture.

Live shipment creation remains final and disabled for every fixture.

## Preview workflow

Run:

```text
make provider-contract-preview
```

The command prints compact boxed tables and writes:

```text
reports/previews/provider_adapter_contract_preview.json
```

The preview demonstrates:

- registered synthetic providers;
- capability discovery;
- recipient validation;
- address validation;
- a preview-only shipment envelope;
- unsupported tracking;
- unsupported quote lookup;
- normalized live-write-disabled error.

## Validation workflow

Run:

```text
make provider-contract-check
```

The validation checks:

```text
preview_only = true
live_write = false
provider_call_performed = false
```

It also verifies the expected provider inventory and normalized
error taxonomy.

## Safety

The fixtures must not:

- perform network calls;
- load credentials;
- create shipments or TTNs;
- book taxis or couriers;
- mutate provider state;
- contain real recipient information;
- select a provider by final business price.
