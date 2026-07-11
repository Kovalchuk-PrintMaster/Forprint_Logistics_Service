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