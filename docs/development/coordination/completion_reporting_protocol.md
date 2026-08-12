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

## Candidate Completion Exchange v0.3 reference validation

Completion Exchange v0.3 is candidate/reference validation only; v0.2 remains operational current until separate Blueprint promotion. Tracking Events is the bounded reference case.

Use `make tracking-events-v0-3-reference-completion-check PACKET=<path>` for the module-local candidate validator. This target is reference-specific and is not a parallel normal runtime path.

Reference preparation does not authorize commit, push, Blueprint ACCEPT/RETURN, protocol promotion, Telegram dependency release, provider calls, database implementation, or production rollout. After separate operator publication, Blueprint candidate intake must use `--allow-candidate-reference`; a green result is `REFERENCE_VALIDATION_READY`, not `ACCEPTED`.

## Candidate v0.3 hardened execution evidence

The bounded Tracking Events Completion Exchange v0.3 reference packet records
one machine-readable `check_results` item for each required Blueprint check ID.
`status: passed` alone is not sufficient. Every required check result also
records the exact command, `exit_code: 0`, a timezone-aware ISO-8601
`executed_at`, and `execution_evidence.output_sha256` computed from the exact
merged stdout/stderr bytes captured for that execution.

### `git status --short`

Exit code zero only means Git executed successfully. During this prepublication
slice, success means the actual dirty path set is exactly the declared six-path
v0.3 reporting/tooling mutation surface. The packet therefore records both the
allowed and observed path sets plus explicit `unexpected_paths` and
`missing_expected_paths`.

### Temporary-index precommit surface validation

Ordinary `git diff --check` does not inspect new untracked files. The candidate
validator therefore proves the real Git index is clean, captures worktree
status, creates an isolated `GIT_INDEX_FILE`, seeds it with `git read-tree
HEAD`, stages only the exact declared paths with `git add -A -- <paths>`,
proves the temporary staged path set equals the declared set, runs `git diff
--cached --check -- <paths>`, and then proves the real Git index bytes/staged
state and worktree status did not change.

Committed evidence contains compact hashes, timestamps, exit codes, exact path
observations, and the precommit result. Large command output remains
local/ignored diagnostics. This candidate mechanism authorizes neither real
index staging, commit, push, Blueprint acceptance, v0.3 promotion, Telegram
release, nor production writes.
