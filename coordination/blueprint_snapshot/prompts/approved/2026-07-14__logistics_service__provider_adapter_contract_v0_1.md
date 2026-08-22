# Logistics Service Provider Adapter Contract v0.1

## Prompt metadata

```yaml
prompt_id: logistics_service_provider_adapter_contract_v0_1
sequence: 4
target_module: logistics_service
phase: provider_adapter_contract_v0_1
priority: high
source_module: forprint_system_blueprint
status: approved
created_at: '2026-07-14'
```

## Purpose

Formalize the provider-neutral adapter contract that will support future Nova Poshta, Ukrposhta, SAT, Meest, taxi and local courier integrations without coupling Logistics Service to one provider and without enabling live provider writes.

This prompt continues the accepted work:

```text
logistics_service_boundary_and_local_model_v0_1
logistics_service_test_address_book_v0_1
```

Blueprint acceptance evidence:

```text
coordination/review_packets/logistics_service/processed/
2026-07-14__logistics_service_test_address_book_v0_1__accepted.yaml
```

## Required reading before implementation

Read the current Blueprint copies through the module's approved Blueprint pull and awareness workflow.

Required sources:

```text
coordination/standards/testing_and_check_report_standard.md
coordination/standards/visual_interface/index.yaml
coordination/standards/governance/module_prompt_execution_and_reporting_protocol.md
coordination/directives/global/active/
2026-07-14__global__directive__compact-report-output-v0-1.md
coordination/roadmaps/logistics_service.yaml
```

For visual output, read the visual-interface index first and then review the active or applicable table, status and color documents referenced by that index.

Do not guess color semantics or table conventions when the Blueprint standard already defines them.

## Starting point

The module already contains an initial provider-neutral foundation:

```text
app/domain/providers.py
app/adapters/providers/base.py
app/domain/shipments.py
app/domain/tracking.py
config/providers.example.yaml
scripts/diagnostics/run_logistics_checks.py
```

The existing code is a starting point. Refine and extend it rather than creating a competing adapter hierarchy.

## Main implementation scope

### 1. Provider capability contract

Review and formalize provider capability semantics.

The contract should support capability discovery for operations such as:

```text
recipient validation;
address validation;
shipment payload preview;
tracking lookup;
provider metadata/capability description;
future delivery quote lookup;
future live shipment creation as an explicitly unavailable capability.
```

Requirements:

```text
capability values are provider-neutral;
capability discovery is deterministic;
unsupported capabilities have an explicit result;
live write capability remains unavailable;
no provider credentials appear in domain models.
```

### 2. Typed adapter request and result models

Introduce or refine typed provider-neutral contracts for:

```text
recipient validation request/result;
address validation request/result;
shipment payload preview request/result;
tracking request/result;
provider capability description;
dry-run execution metadata.
```

Do not return loosely structured dictionaries as the only public service boundary where a typed contract is practical.

Provider-specific payload details may remain inside a safe preview payload field, but the outer result must remain provider-neutral and validated.

### 3. Dry-run payload envelope

Create a stable dry-run payload preview contract.

It should identify:

```text
provider_id;
operation;
schema/version;
request correlation reference;
preview_only state;
live_write state;
normalized input summary;
provider payload preview;
validation messages;
warnings;
generated artifacts or preview paths when applicable.
```

The envelope must make it impossible to confuse a preview with a live provider mutation.

### 4. Provider error taxonomy

Add a provider-neutral error taxonomy.

At minimum distinguish:

```text
invalid request;
unsupported capability;
recipient validation failure;
address validation failure;
provider configuration unavailable;
provider authentication unavailable;
provider temporarily unavailable;
provider rate limited;
provider response invalid;
tracking reference invalid;
live write disabled;
unexpected provider error.
```

Requirements:

```text
errors are machine-readable;
human-readable safe messages are available;
secrets and raw sensitive provider responses are not exposed;
retryability is explicit where meaningful;
provider-specific errors can be normalized later.
```

### 5. Provider adapter interface

Refine the existing `ProviderAdapter` boundary.

The interface should clearly separate:

```text
capability description;
validation;
dry-run payload preview;
read-only tracking;
future quote/read operations;
forbidden live mutations.
```

Do not duplicate the existing adapter base under another architecture.

Keep a single provider-neutral source of truth for the adapter contract.

### 6. Adapter registry or resolver

Add a small local registry/resolver if it improves contract validation.

It may support:

```text
registration by provider_id;
lookup by provider_id;
capability filtering;
duplicate provider rejection;
disabled-provider visibility;
safe provider description.
```

It must not:

```text
load production credentials;
perform network calls;
auto-enable providers;
create shipments;
select a provider using final business pricing.
```

### 7. Synthetic contract fixtures

Add safe synthetic examples for several provider classes.

Recommended coverage:

```text
Nova Poshta-like parcel provider;
Ukrposhta-like postal provider;
generic freight provider;
generic taxi/courier provider.
```

These are contract fixtures only.

Do not implement real provider SDK calls, HTTP calls or production payload submission.

### 8. Preview and validation workflow

Add a human-readable provider adapter contract preview.

The preview should demonstrate:

```text
registered providers;
capabilities;
supported/unsupported operation result;
synthetic shipment preview envelope;
normalized provider error example;
tracking contract example;
live provider write disabled.
```

Expose it through the existing Make-first workflow where practical.

## Reporting alignment subtask

Align Logistics Service reporting with the current Blueprint reporting and visual-interface standards.

This is a bounded alignment task and must not replace the provider adapter contract work.

### Routine compact mode

`make check-report` should:

```text
use one or more boxed tables;
group unrelated concerns into separate compact tables when that improves readability;
use the standard Blueprint status/color semantics;
show errors, warnings and blockers clearly;
show stable paths to detailed JSON/Markdown reports;
avoid printing full successful test streams and repeated logs.
```

The routine report should be as small as practical for fast analysis.

A guideline near or below 100 terminal lines is preferred for a normal module, but this is not a hard limit. The architecture and number of independent concerns control the necessary size.

Examples of separate tables where useful:

```text
core code quality and tests;
provider contract checks;
safety and boundary checks;
coordination and prompt state.
```

### Extended diagnostics mode

Add or document:

```text
make check-report-full
```

The extended command may be as detailed as necessary.

Large output should be redirectable to a stable diagnostic file, for example:

```text
reports/diagnostics/logistics_service_check_report_full.log
```

Routine output must not hide warnings or failures. Extended diagnostics complement compact output; they do not replace it.

### Visual conventions

Use the active/applicable standards referenced by:

```text
coordination/standards/visual_interface/index.yaml
```

Where a table displays a current prompt, current roadmap step or currently selected provider/check group, use the standard current-row marker convention when applicable.

Do not invent a new incompatible palette.

## Documentation

Add or update documentation covering:

```text
provider adapter contract;
capability semantics;
typed request/result models;
dry-run payload envelope;
provider error taxonomy;
adapter registry/resolver if added;
live-write prohibition;
future provider-specific adapter extension rules;
compact and extended reporting commands.
```

Recommended locations:

```text
docs/architecture/provider_adapter_contract.md
docs/architecture/boundaries/provider_adapter_boundary.md
docs/development/testing/provider_contract_fixtures.md
docs/development/testing/check_report_modes.md
```

Use existing equivalent files when they already exist instead of duplicating documentation.

## Required tests

Add or update tests for:

```text
capability discovery;
unsupported capability behavior;
typed request/result validation;
preview-only envelope invariants;
live-write disabled invariants;
error taxonomy and retryability;
safe error rendering;
adapter registry duplicate rejection;
provider lookup;
synthetic fixtures;
preview workflow;
no secrets;
no real provider calls;
no provider-specific ownership leakage;
compact report generation;
extended report command availability;
report artifact creation.
```

## Required commands

Run at minimum:

```text
make governance-check
make coordination-check
make check
make check-report
make check-report-full
git diff --check
git status --short
```

For a very large extended report, redirect it to a file and return only the compact summary and artifact path.

## Required completion workflow

Use the module-side completion packet automation.

Required module-side outputs:

```text
coordination/reports/completion/
coordination/reports/index.yaml
coordination/status/current_status.yaml
coordination/status/current_status.md
coordination/status/next_questions_for_blueprint.md
coordination/completion_packets/records/
```

The completion packet and report must include:

```text
prompt id;
branch;
implementation commit;
completion commit;
implemented contract changes;
reporting alignment changes;
tests and check totals;
warnings and blockers;
artifact paths;
explicit live-write-disabled confirmation;
explicit no-real-credentials confirmation;
explicit no-real-provider-call confirmation;
boundary confirmation;
open questions or explicit no-open-questions.
```

The final assistant handoff should use compact tables and provide paths to detailed evidence rather than reproducing raw logs.

## Explicit non-goals

Do not implement:

```text
live Nova Poshta API calls;
live Ukrposhta API calls;
live SAT or Meest calls;
live taxi/courier order creation;
real TTN creation;
provider credential loading for production use;
automatic shipment submission;
automatic provider mutation;
production background workers;
production queues;
production database migration;
canonical client ownership;
canonical order ownership;
final customer price ownership;
payment or accounting writes;
warehouse stock mutation;
CRM changes;
Telegram Bot changes;
Website changes;
Calculator changes;
Integration Gateway writes.
```

## Definition of done

The prompt is complete when:

```text
one provider-neutral adapter contract is authoritative;
capability semantics are explicit;
typed request/result models exist;
dry-run payload previews are unmistakably non-live;
provider errors have a normalized taxonomy;
synthetic fixtures and previews exist;
live writes remain impossible;
tests and governance checks pass;
compact boxed reporting follows Blueprint visual conventions;
extended diagnostics are available;
report artifacts are generated;
completion packet is valid and idempotent;
module changes are committed and pushed;
Blueprint receives the final completion evidence.
```
