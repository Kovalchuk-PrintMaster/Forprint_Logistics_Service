
# Tracking Events v0.4 command-semantics migration

This bounded implementation slice repairs the Logistics completion workflow
semantics required by the Tracking Events v0.4 reference-completion migration.

Tracking runtime/domain/service files are not modified.

## Read-only commands

- `make check-report`
- `make check-report-full`
- `make module-validate`
- `make completion-packet-check`
- `make completion-packet-v0-4-validate PACKET=<path>`
- `make completion-outbox-v0-4-validate EVENT=<path>`

`completion-packet-check` no longer invokes `completion-packet-apply`.
`module-validate` no longer performs `report-clean` or `status-report`.
`check-report` and `check-report-full` render results in memory.

## Explicit mutation commands

- `make check-report-generate`
- `make check-report-full-generate`
- legacy `make completion-packet-apply PACKET=<path>`

## v0.4 validators

The module owns semantics-equivalent local adaptations of the canonical
Blueprint v0.4 Completion Packet and Completion Outbox validators from
Blueprint commit `3940c70f4fbe56aa8f8c834d8cbee56eeb8b5c11`.

The only local changes are three Ruff `SIM102` nested-if normalizations.
Canonical validation behavior and field semantics remain unchanged.

The Outbox validator reads the Blueprint coordination source registry and does
not write to Blueprint.

## Safety

No provider call/write, Telegram API call, production DB implementation,
cross-repository write, staging, commit, push, Blueprint decision, or global
v0.4 promotion is performed by this slice.
