# ForPrint Logistics Service

ForPrint Logistics Service owns provider-neutral logistics boundaries,
delivery requests, shipment drafts and previews, tracking status and logistics
provider adapter behavior.

## Module identity

- Module ID: `logistics_service`
- Repository directory: `forprint_logistics_service`
- Python: 3.11.2
- Virtual environment: `.venv_logistics_service`

## Current checkpoint

`bootstrap_and_coordination_foundation_v0_1`

The current implementation is local and preview-oriented.

It does not perform live provider writes.

## Safe development workflow

```bash
source .venv_logistics_service/bin/activate
make install
make governance-check
make check
Architectural boundary

The module may own logistics provider adapters, delivery requests, shipment
drafts, payload previews, tracking status and logistics notification events.

It must not own canonical clients, canonical orders, product or material
catalogs, price calculation, accounting documents, payment truth, warehouse
stock truth, production tasks or channel session state.

Provider safety

Provider adapters may validate local data, build payload previews and support
tracking reads.

Shipment creation and all other live provider mutations are disabled.

Secrets

Real provider credentials must not be committed.

Use an ignored local .env file only after a future approved integration
checkpoint.


## `docs/boundary.md`

```markdown
# Logistics Service boundary

## Owned responsibility

Logistics Service owns:

- logistics provider boundaries;
- provider capability metadata;
- delivery requests;
- shipment drafts;
- provider payload previews;
- tracking status and events;
- logistics notification events;
- provider adapter behavior;
- provider response snapshots and logistics audit records when later approved.

## Consumed references

The module may consume references to:

- canonical orders;
- canonical clients;
- package descriptions.

Those references remain owned by their canonical source modules.

## Forbidden ownership

Logistics Service must not own:

- canonical clients;
- canonical orders;
- product or material catalogs;
- price calculation;
- accounting documents;
- payment truth;
- warehouse stock truth;
- production tasks;
- Telegram conversation state;
- Website session state.

## Channel role

Telegram Bot, Website and CRM are interaction or coordination surfaces.

They do not own provider credentials, shipment truth or provider integration
history.