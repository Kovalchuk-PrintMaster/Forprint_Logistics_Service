# Logistics Service current completion reporting protocol

## Current protocol

All new and superseding completion evidence uses one current path:

- `module_completion_packet_v0_2`;
- `blueprint_completion_intake_v0_2`;
- `scripts/coordination/validate_completion_packet.py`;
- `scripts/coordination/apply_completion_packet.py`;
- `scripts/coordination/validate_completion_report.py`;
- `scripts/validation/check_completion_safety_boundaries.py`;
- `coordination/completion_packets/templates/module_completion_packet_v0_2.example.yaml`.

Historical packets are immutable evidence and are not rewritten to satisfy the current schema.

## Workflow

1. Complete implementation and focused tests.
2. Run `make completion-safety-check`.
3. Copy the current template into `coordination/completion_packets/records/`.
4. Fill factual evidence and a full 40-character `implementation_commit`.
5. For a correction, set both `supersedes_completion_id` and `revision_reason`.
6. Run `make completion-packet-check PACKET=<path>`.
7. Run the full module validation gate.
8. Review exact changed paths.
9. Commit manually and push manually.
10. Derive the completion commit with `git rev-parse HEAD`.
11. Notify Blueprint with packet path, completion commit and branch.

The completion commit is not recursively embedded into the packet. Blueprint intake receives it separately and verifies Git ancestry and remote containment.

## Safety confirmations

Current packets require boolean `true` for:

- `no_production_api`;
- `no_live_external_integrations`;
- `no_real_1c_sync`;
- `no_production_write`;
- `no_automatic_posting`.

Strings such as `"true"` are invalid.

## Superseding semantics

Never overwrite a published historical packet. Create a new completion ID using the current schema and pair `supersedes_completion_id` with `revision_reason`.

## Review boundary

A green Blueprint intake can produce `READY_FOR_OPERATOR_REVIEW`. It does not mean `ACCEPTED`. Logistics Service never creates automatic ACCEPT/RETURN decisions.
