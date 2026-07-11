# Logistics Service configuration

This directory contains committed non-secret configuration and safe examples.

## Allowed content

- module identity;
- non-secret feature flags;
- provider capability declarations;
- safe adapter defaults;
- environment variable names;
- disabled-by-default integration settings.

## Forbidden content

Do not commit:

- real provider API keys;
- access tokens;
- passwords;
- private client or recipient data;
- production connection details;
- enabled production-write configuration.

Real local credentials belong in an ignored `.env` file or another approved
local secret store.

## Safety default

Live provider writes are disabled.

Adding credentials must not automatically enable shipment creation or any other
provider-side mutation.