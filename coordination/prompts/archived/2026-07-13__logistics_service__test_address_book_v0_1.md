# Prompt: Logistics Service Test Address Book and Recipient Fixtures v0.1

## Target module

`logistics_service`

## Prompt ID

`logistics_service_test_address_book_v0_1`

## Purpose

Create a controlled local test address book foundation for Logistics Service.

The goal is to make recipient lookup, recipient aliases, shipment-time address snapshots and local address book examples practical for future Telegram Bot, CRM, Website and operator workflows without making Logistics Service the owner of canonical clients.

This checkpoint must remain local, non-canonical, preview-only and safe.

Do not add live provider API integration.

Do not create real shipments.

Do not create TTNs.

Do not add real provider credentials.

Do not commit real client or recipient private data.

## Current context

Logistics Service has completed and Blueprint is accepting:

- `logistics_service_bootstrap_and_coordination_foundation_v0_1`;
- `logistics_service_boundary_and_local_model_v0_1`.

Known latest completion evidence for local model:

```text
Implementation commit: 3b724d0d1dea9c5c5a95940bb61233fc3cdbb1f8
Completion commit: 6b9bab3
Completion report: coordination/reports/completion/logistics_service_boundary_and_local_model_v0_1_completion.md
Completion packet: coordination/completion_packets/records/2026-07-12__logistics_service__boundary_and_local_model_v0_1_completion.yaml
Tests: 51 passed
Check report: 8 passed / 0 warnings / 0 failed
Governance check: passed
Coordination metadata: 0 errors, 0 warnings
```

## The local model foundation already includes:

provider-neutral provider references;
non-canonical recipient references;
shipment-time address snapshots;
preview-only shipment drafts;
local-only tracking requests;
local tracking events;
local notification payloads;
LogisticsRepository protocol;
InMemoryLogisticsRepository;
shipment/tracking/notification services;
workflow examples;
local model preview;
boundary validation.
Repository

## Expected working directory:

/srv/software_development/forprint-project/forprint_logistics_service

Do not write into the Blueprint repository from the module side.

Strategic boundary

Logistics Service may own:

logistics recipient references;
logistics address book entries;
recipient aliases and lookup hints;
shipment-time address snapshots;
local non-canonical test fixtures;
local address book preview workflows;
address book validation helpers;
future handoff-ready logistics recipient references.

## Logistics Service must not own:

canonical clients;
canonical client accounts;
canonical orders;
product catalog;
material catalog;
price calculation;
accounting truth;
payment truth;
warehouse stock truth;
production task ownership;
Telegram conversation state;
CRM client truth;
Website session state.

## Safety policy

This checkpoint must not perform live provider writes.

Do not implement:

real Nova Poshta TTN creation;
real Ukrposhta shipment creation;
real SAT shipment creation;
real Meest shipment creation;
real Uklon/Bolt/Uber order creation;
automatic courier/taxi calls;
live provider write of any kind;
production API;
1C write;
payment write;
stock mutation;
canonical order creation;
canonical client database;
real client database;
real committed customer recipient list.

All committed address book examples must be synthetic.

If the module introduces a path for local owner-maintained real recipient data, that file must be ignored by git and documented as local-only.

## Required implementation

Build a local test address book foundation on top of the existing local model.

Inspect current files before changing them.

Likely files to inspect or update:

app/domain/recipients.py
app/services/
app/storage/repositories.py
app/storage/in_memory.py
examples/fixtures/recipients/test_recipients.yaml
examples/workflows/
scripts/previews/
scripts/validation/
docs/development/testing/local_test_data_policy.md
docs/architecture/boundaries/local_logistics_model_boundary.md
tests/
Makefile

## The assistant may add small focused modules if useful, for example:

app/domain/address_book.py
app/services/address_book_service.py
examples/fixtures/address_book/test_address_book.yaml
examples/workflows/address_book_lookup_preview.yaml
scripts/previews/preview_test_address_book.py
scripts/validation/check_test_address_book.py
docs/architecture/boundaries/test_address_book_boundary.md
tests/unit/services/test_address_book_service.py
tests/unit/storage/test_address_book_repository.py
tests/contract/fixtures/test_address_book_fixture.py
tests/integration/workflows/test_address_book_preview.py

Keep the structure simple.

Do not add a production database.

Do not add FastAPI.

Do not add systemd.

Do not add provider SDKs.

Do not add external API clients.

## Required local address book behavior

Implement or confirm local support for:

Address book entries

Each entry should be non-canonical and logistics-owned only as an operational logistics reference.

Recipient aliases

Entries may have aliases such as:

офіс
склад
тестовий отримувач
київський отримувач

Committed aliases must be synthetic or generic.

Recipient lookup

Add local lookup behavior by:

recipient reference;
alias;
display name or safe search token;
optional city/area hint.

Shipment-time address snapshots

Address snapshots must remain snapshots used for shipment drafts, not canonical address ownership.

Address book to shipment draft preview

Demonstrate that a selected address book entry can be used to create a preview-only shipment draft without provider API calls.

Local repository behavior

Extend the repository protocol and in-memory implementation if needed.

It may support:

save/get/list address book entries;
find by alias;
find by recipient reference;
create shipment address snapshot from an address book entry.

Local-only real data policy

Document that real frequent recipients may later be maintained by the owner in a local ignored file, but this checkpoint must not commit real recipient private data.

## Required examples

Add or update synthetic examples.

Recommended:

examples/fixtures/address_book/test_address_book.yaml
examples/workflows/address_book_lookup_preview.yaml

Examples must clearly state:

non_canonical: true
preview_only: true
live_provider_write: false
synthetic_data: true
real_customer_data: false

The example should include at least three synthetic address book entries:

one Kyiv/local recipient;
one warehouse-like recipient;
one office-like recipient.

Do not use real customer names, real phones, real private addresses or real provider account data.

## Required preview

Add a human-readable preview command if practical.

Recommended target:

make test-address-book-preview

or a script:

scripts/previews/preview_test_address_book.py

The preview should show:

Test address book: local synthetic entries
Entry count: 3
Lookup by alias: OK
Recipient reference: non-canonical
Address snapshot: shipment-time snapshot
Shipment draft preview: created without provider API call
Live provider write: disabled

## Required docs

Add or update documentation:

docs/architecture/boundaries/test_address_book_boundary.md
docs/development/testing/local_test_data_policy.md
docs/architecture/boundaries/local_logistics_model_boundary.md

Docs must explain:

what the test address book is;
why it is not a canonical client database;
how recipient aliases differ from client identity;
how address snapshots differ from canonical addresses;
how future Telegram Bot / CRM / Website consumers may reference address book entries;
how real local frequent recipients may be handled safely without committing private data;
why live provider writes remain disabled.

## Required Makefile/check-report visibility

Expose the new validation or preview through the make-first workflow where practical.

Do not rewrite the Makefile broadly.

Recommended new or updated targets:

make test-address-book-preview
make test-address-book-check
make logistics-check
make check-report

The check report should include visibility for test address book validation if a new validator or preview is added.

## Required tests

Add or update tests for:

address book entry model is non-canonical;
aliases are present and searchable;
lookup by alias works;
lookup by recipient reference works;
shipment-time address snapshot can be derived from address book entry;
address book entry can be used to create preview-only shipment draft;
repository save/get/list/search behavior;
fixtures are synthetic and non-canonical;
examples validate;
preview script renders expected output;
no secrets are introduced;
no real customer/private recipient data is committed;
no forbidden ownership fields are introduced;
live provider writes remain disabled.

Run:

make governance-check
make check
make check-report
git diff --check
git status --short

## Required completion and reporting workflow

At the end of this task, prepare a module-side completion packet inside the Logistics Service repository.

Use the completion packet automation if available.

Required module-side files:

coordination/reports/completion/<prompt_id>_completion.md
coordination/reports/index.yaml
coordination/status/current_status.yaml
coordination/status/current_status.md
coordination/status/next_questions_for_blueprint.md
coordination/completion_packets/records/<record>.yaml

Required completion report content:

prompt id;
branch;
implementation commit;
completion commit;
summary of implemented work;
files changed;
checks passed;
known warnings;
explicit no-live-provider-write confirmation;
explicit secrets policy confirmation;
explicit no-real-customer-data confirmation;
explicit boundary confirmation;
confirmation that no Blueprint files were written directly;
open questions for Blueprint, or explicit “No open questions”.

Status/report formatting requirements:

keep current_status.yaml valid YAML;
keep current_status.md readable Markdown;
close all Markdown code fences;
keep only current open questions in next_questions_for_blueprint.md;
ensure all text files end with a newline.

## Blueprint reporting boundary

Logistics Service may read Blueprint prompts and standards.

Logistics Service must not write directly into:

/srv/software_development/forprint-project/forprint_system_blueprint/

Blueprint-side incoming report registration and Blueprint review are separate Blueprint-owned actions.

## Explicit non-goals

Do not implement:

live Nova Poshta API integration;
live Nova Poshta TTN creation;
live Ukrposhta/SAT/Meest writes;
live Uklon/Bolt/Uber order creation;
automatic courier/taxi calls;
production daemon/service;
systemd unit;
real provider credentials;
real customer recipient database;
canonical client database;
canonical order database;
product catalog;
price calculation;
payment status changes;
warehouse stock reservation;
1C integration;
Telegram Bot code changes;
Website code changes;
CRM code changes;
Calculator code changes;
Integration Gateway writes;
production database.

## Definition of done

This prompt is complete when:

local test address book foundation exists;
address book entries are non-canonical;
synthetic fixture examples exist;
alias lookup works;
shipment-time address snapshot creation works;
preview-only shipment draft can be created from address book entry;
repository behavior is covered;
examples exist and validate;
preview exists;
tests are green;
check report is green;
live provider writes remain disabled;
no real credentials are committed;
no real customer/private recipient data is committed;
no forbidden ownership is added;
completion packet is created inside Logistics Service repo;
final module commit hash is reported back to Blueprint.
