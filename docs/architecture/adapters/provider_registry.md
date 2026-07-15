# Provider Registry

## Purpose

`ProviderRegistry` is a small process-local resolver for the
provider-neutral adapter contract.

It supports:

- explicit registration by provider ID;
- deterministic lookup;
- duplicate provider rejection;
- capability filtering;
- disabled-provider visibility;
- safe provider descriptions.

## Registration rule

Providers are disabled by default.

Registration may explicitly set `enabled=True` for a controlled
local fixture or later approved runtime configuration. The registry
does not auto-enable providers.

Provider IDs are matched case-insensitively for duplicate detection
and lookup.

## Safe description

`ProviderRegistryDescription` exposes:

- provider ID;
- display name;
- enabled state;
- registration source;
- typed capability description;
- `live_write_enabled = false`.

It does not expose:

- adapter instances;
- provider SDK clients;
- credentials;
- API keys or tokens;
- raw provider responses.

## Resolver behavior

Normal `resolve()` rejects a disabled provider.

A caller may request `include_disabled=True` only for local
inspection, contract validation or safe preview workflows.

Unknown and disabled providers have separate explicit exceptions.

## Non-goals

The registry does not:

- load production credentials;
- read production provider configuration;
- perform HTTP or SDK calls;
- create shipments or TTNs;
- mutate provider-side state;
- auto-enable providers;
- calculate final customer pricing;
- automatically select a provider by price.
