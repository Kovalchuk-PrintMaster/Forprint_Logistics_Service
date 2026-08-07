# Logistics Service coordination

This directory contains module-local coordination records for ForPrint
Logistics Service.

## Ownership boundary

Files in this directory belong to the Logistics Service repository.

Module-side automation may update these local coordination records, but it must
not write directly into the ForPrint System Blueprint repository.

Blueprint-side intake, review, acceptance metadata and received report copies
remain Blueprint-owned actions.

## Main files

- `blueprint_source.yaml` — readable Blueprint source locations.
- `prompts/index.yaml` — prompts received by this module.
- `prompts/received/` — locally synchronized prompt copies.
- `reports/index.yaml` — module completion and commit report index.
- `reports/completion/` — completion reports.
- `reports/commits/` — commit/checkpoint reports when required.
- `status/current_status.yaml` — machine-readable current status.
- `status/current_status.md` — human-readable current status.
- `status/next_questions_for_blueprint.md` — current architectural questions.
- `blueprint_awareness/` — reviewed Blueprint document records.

## Validation

Coordination YAML files must be valid, contain no unresolved placeholders and
be checked before commit.

## Automated prompt lifecycle

- `prompts/received/` stores all synchronized approved prompts.
- `prompts/active/` stores exactly one current prompt.
- `prompts/archived/` stores previous inactive prompts.
- `prompts/index.yaml` is updated by prompt intake automation.

Use `make blueprint-prompts-sync` instead of editing prompt metadata
manually.

## Current completion reporting

The active completion path is documented in `docs/development/coordination/completion_reporting_protocol.md`. New and superseding packets use `module_completion_packet_v0_2` with `blueprint_completion_intake_v0_2`, positive `no_*: true` safety confirmations and full 40-character implementation commits. Historical packets remain immutable. `READY_FOR_OPERATOR_REVIEW` is not `ACCEPTED`.
