# Prompt: Logistics Service Bootstrap and Coordination Foundation v0.1

## Target module

`logistics_service`

## Prompt ID

`logistics_service_bootstrap_and_coordination_foundation_v0_1`

## Purpose

Create the first controlled foundation for ForPrint Logistics Service.

The goal is to establish a clean module skeleton, make-first workflow, tests, coordination records, provider-neutral logistics boundaries, local non-canonical test data fixtures, and strict safety rules before any live provider API write is introduced.

Logistics Service is planned as the owner of delivery provider boundaries, shipment drafts, tracking truth, provider payload previews, logistics address book and logistics notification events.

## Current architecture context

ForPrint is an operational platform for рекламно-інформаційні продукти.

Telegram Bot is a Tier 1 client communication channel and intake assistant.

Telegram Bot must not own shipment truth, delivery provider credentials, provider integrations or logistics history.

Future flow should be:

```text
Telegram Bot / Website / CRM / Calculator
        ↓
Integration Gateway or approved internal contract
        ↓
Logistics Service
        ↓
Provider adapter
        ↓
Delivery provider API
```

At this stage, the Integration Gateway link may remain a future contract. The bootstrap must focus on local module foundation and safe internal models.

## Repository

Expected working directory:

/srv/software_development/forprint-project/logistics_service

If the directory already exists, inspect it first and preserve any existing useful files.

If it is empty or not initialized, create a minimal Python project skeleton inside this module directory only.

Do not write into the Blueprint repository.

## Strategic boundary

Logistics Service may own:

logistics provider catalog;
provider adapter boundaries;
provider capability metadata;
logistics address book / recipient references;
shipment drafts;
shipment request previews;
provider payload previews;
tracking requests;
tracking events;
logistics notification events;
provider response snapshots;
logistics audit trail.

Logistics Service must not own:

canonical clients;
canonical orders;
product catalog;
material catalog;
price calculation;
accounting documents;
payment truth;
warehouse stock truth;
production tasks;
Telegram conversation state;
Website session state.
## Safety policy

This checkpoint must not perform live provider writes.

Do not implement:

real Nova Poshta TTN creation;
real Ukrposhta shipment creation;
real SAT shipment creation;
real Uklon/Bolt/Uber order creation;
automatic courier/taxi calls;
live provider write of any kind;
1C write;
payment write;
stock mutation;
canonical order creation.

All live-write capabilities must remain disabled by default.

Any future live provider write must require explicit later prompt approval, dry-run controls, manual confirmation controls, environment safety checks and audit records.

## Secrets policy

Do not commit real provider credentials.

Do not commit real API keys.

Do not commit .env with secrets.

Add only safe examples such as:

config/secrets.example.env

or:

config/providers.example.yaml

Real local secrets should be ignored by git and documented as local-only.

## Required project skeleton

Create or verify a practical initial structure similar to:

logistics_service/
  app/
    __init__.py
    domain/
      __init__.py
    services/
      __init__.py
    adapters/
      __init__.py
      providers/
        __init__.py
    storage/
      __init__.py
    config/
      __init__.py
  tests/
    __init__.py
  scripts/
  docs/
  config/
  coordination/
    prompts/
      active/
      archived/
    reports/
      completion/
    status/
    standards/
  examples/
    fixtures/
  runtime/
    .gitkeep
  Makefile
  pyproject.toml
  README.md
  .gitignore

Adjust the exact structure if the existing module layout already has a better convention, but keep it simple and consistent.

Do not add broad framework complexity.

## Required domain drafts

Add minimal provider-neutral domain drafts.

Suggested files:

app/domain/providers.py
app/domain/recipients.py
app/domain/shipments.py
app/domain/tracking.py
app/domain/events.py

These files may contain simple dataclasses or typed models.

Minimum concepts:

LogisticsProvider
ProviderCapability
RecipientRef
AddressSnapshot
ShipmentDraft
ShipmentStatus
TrackingRequest
TrackingEvent
LogisticsNotificationEvent

Keep them provider-neutral.

Do not hard-code the service around Nova Poshta only.

## Required adapter draft

Add a provider adapter interface draft.

Suggested file:

app/adapters/providers/base.py

It should define a small provider adapter protocol or base class for future operations such as:

validate recipient/address;
build shipment payload preview;
track shipment;
list or describe provider capabilities;
create shipment only as future disabled capability.

The live create-shipment operation must not be active in this checkpoint.

If a method is included for future create shipment, it must raise a clear disabled/not implemented error unless explicit future safety gates are provided.

## Required local fixture

Add a small non-canonical local fixture format for recipients.

Suggested file:

examples/fixtures/test_recipients.yaml

Use placeholder or safe test data.

If real frequent recipients are later added manually by the owner, document that the fixture is local/testing and not canonical client ownership.

The fixture must be clearly marked:

non_canonical: true
purpose: local logistics testing only
## Required Makefile targets

Add a make-first workflow.

At minimum:

make check
make test
make lint
make format
make report-status

If lint/format tools are not installed yet, the target may be a safe placeholder or call a basic Python compile/test check, but it must not be misleading.

Recommended:

make logistics-check
make coordination-check

make check should call the currently meaningful checks.

## Required tests

Add tests from the first checkpoint.

At minimum:

import/domain model smoke test;
provider adapter disabled live write safety test;
fixture loading test;
no real secrets committed policy test if practical;
Makefile check target green.

Suggested tests:

tests/test_domain_models.py
tests/test_provider_adapter_safety.py
tests/test_fixtures.py
## Required documentation

Add or update:

README.md
docs/boundary.md
docs/secrets_policy.md
docs/provider_adapter_policy.md
docs/local_test_data_policy.md

Documentation must clearly state:

Logistics Service owns logistics provider boundaries and shipment/tracking truth;
Telegram Bot is only a channel UI / notification surface;
test address book is non-canonical;
live provider write is disabled by default;
provider credentials must not be committed to git.
## Required coordination files

Create or update module-side coordination files inside the Logistics Service repository:

coordination/status/current_status.yaml
coordination/status/current_status.md
coordination/status/next_questions_for_blueprint.md
coordination/reports/completion/logistics_service_bootstrap_and_coordination_foundation_v0_1_completion.md
coordination/reports/index.yaml

Do not write any completion report directly into the Blueprint repository.

## Required completion and reporting workflow

At the end of this task, prepare a module-side completion packet inside the Logistics Service repository.

Inspect available automation before manual report edits:

find scripts -maxdepth 3 -type f | sort | grep -E 'completion|coordination|report|status|packet' || true
find coordination -maxdepth 3 -type f | sort
make help 2>/dev/null | grep -E 'completion|coordination|report|status|packet' || true

If completion packet automation exists, use it.

If completion packet automation is missing or incomplete, manual updates are allowed for this bootstrap checkpoint, but the completion report must explicitly say:

Completion packet automation was not available or was deferred for this module step.
The required module-side coordination files were updated manually inside the Logistics Service repository.
No files were written directly into the Blueprint repository.

Required completion report content:

prompt id;
branch;
final commit hash;
summary of implemented work;
files changed;
checks passed;
known warnings;
explicit boundary confirmation;
explicit secrets policy confirmation;
explicit no-live-provider-write confirmation;
confirmation that no Blueprint files were written directly;
open questions for Blueprint, or explicit “No open questions”.

Status/report formatting requirements:

keep current_status.yaml valid YAML;
keep current_status.md readable Markdown;
close all Markdown code fences;
keep only current open questions in next_questions_for_blueprint.md;
ensure all text files end with a newline.
## Required checks

Run or create equivalent checks:

python -m py_compile $(find app scripts tests -name '*.py' -type f | sort)
python -m pytest -q
make check

If pytest is not available yet, add it to project dev dependencies or document why a temporary fallback is used.

Before commit:

git diff --check
git status --short
git log -5 --oneline
## Branch and commit

Suggested branch:

feature/logistics-bootstrap-coordination-v01

Commit after green checks.

Push after commit if the remote is configured.

If no remote is configured yet, report that clearly and provide the final local commit hash.

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
canonical client database;
canonical order database;
product catalog;
price calculation;
payment status changes;
warehouse stock reservation;
1C integration;
Telegram Bot code changes;
Website code changes;
Calculator code changes;
Integration Gateway writes.
## Definition of done

This prompt is complete when:

Logistics Service repository has a clean initial skeleton;
make-first workflow exists;
tests exist and pass;
provider-neutral domain drafts exist;
provider adapter safety boundary exists;
live provider write is disabled by default;
secrets policy is documented;
local non-canonical fixture policy is documented;
module-side coordination files exist;
completion report exists inside Logistics Service repo;
no Blueprint files were written directly by the module assistant;
final commit hash is reported back to Blueprint.

---
