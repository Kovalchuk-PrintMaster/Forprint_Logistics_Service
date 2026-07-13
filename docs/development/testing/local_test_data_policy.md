# Local test data policy

Fixtures under `examples/fixtures/` exist only for local Logistics
Service testing and preview workflows.

Committed fixture data must be:

- synthetic;
- non-canonical;
- free of real customer names;
- free of real phone numbers;
- free of real private addresses;
- free of provider credentials;
- unsuitable for production use.

## Required fixture markers

Recipient and address-book fixtures must clearly declare their safety
state.

```yaml
non_canonical: true
preview_only: true
live_provider_write: false
synthetic_data: true
real_customer_data: false
```

Committed recipient references must use explicit test or synthetic
identifiers.

Committed address lines and display names must be visibly synthetic.

## Forbidden committed data

Do not commit:

- real customer or recipient lists;
- personal phone numbers;
- real private delivery addresses;
- provider account identifiers;
- API keys, tokens or credentials;
- canonical client or account identifiers;
- payment, stock, accounting or 1C truth.

## Local owner-maintained data

Real frequent recipients may later be maintained only in:

```text
runtime/address_book/owner_recipients.yaml
```

This path is ignored by Git and is owner-controlled local runtime
data.

The local file:

- is not a committed fixture;
- is not canonical client ownership;
- is not shared with Blueprint;
- must not contain provider credentials;
- must not enable live provider writes;
- must not be used as production database truth.

The repository must remain fully testable without this local file.
