# Logistics Service boundary

## Owned responsibility

ForPrint Logistics Service owns:

- logistics provider boundaries;
- logistics provider adapter behavior;
- provider capability metadata;
- delivery requests;
- shipment drafts;
- provider payload previews;
- delivery and tracking status;
- tracking events;
- logistics notification events;
- provider response snapshots when later approved;
- logistics audit records when later approved.

## Consumed references

The module may consume references to:

- canonical orders;
- canonical clients;
- package descriptions.

These objects remain owned by their canonical source modules.

A local `RecipientRef` or `AddressSnapshot` is only a logistics reference or
shipment-time snapshot. It does not establish canonical client or address
ownership.

## Provided information

The module may provide:

- delivery status;
- delivery labels;
- delivery cost estimates;
- tracking events;
- shipment payload previews;
- logistics notifications.

Cross-module formats remain subject to approved Blueprint contracts.

## Forbidden ownership

Logistics Service must not own:

- canonical clients;
- canonical orders;
- product catalogs;
- material catalogs;
- price calculation;
- accounting documents;
- payment truth;
- warehouse stock truth;
- production tasks;
- Telegram conversation state;
- Website session state.

## Channel boundary

Telegram Bot, Website and CRM are interaction or coordination surfaces.

They do not own:

- provider credentials;
- provider integration history;
- shipment truth;
- tracking truth.

## Live-write safety

Live provider writes are disabled during
`bootstrap_and_coordination_foundation_v0_1`.

The module must not currently create shipments, TTNs, courier calls, taxi
orders or any other provider-side mutation.