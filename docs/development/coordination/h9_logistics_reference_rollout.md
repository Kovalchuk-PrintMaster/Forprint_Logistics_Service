# H9 Logistics reference rollout

H9 aligns the Logistics repository with the promoted ForPrint coordination
runtime v0.4 and v0.4.1 hardening release without changing Logistics domain
behavior.

Canonical operator commands:

```text
make module-start
make module-sync
make module-status
make module-validate
make coordination-sync-check
make blueprint-check
make blueprint-prompts-list
make prompt-notify
make prompt-next
make prompt-read-next
make check
make governance-check
make git-status
```

`module-start` is fail-closed:

```text
coordination-sync-check
module-sync
module-status
prompt-notify
prompt-read-next
```

The explicit freshness gate uses the module-owned
`scripts/coordination_sync_check.py`. It uses `git ls-remote` only and never
fetches, pulls, updates Blueprint refs, or writes the Blueprint repository.

`module-sync` is network-independent. It reads already-visible Blueprint
inputs and writes only `coordination/blueprint_snapshot/`. The snapshot
contains the current release authority, Prompt Queue v0.2, referenced prompt
artifacts and deterministic source identity metadata.

Prompt readiness comes only from
`module_execution.status=ready_for_module_pull`:

```text
0 -> NO_READY_PROMPT
1 -> READY_PROMPT
>1 -> MULTIPLE_READY_PROMPTS / fail closed
```

Notification and reading do not create CLAIMED, release work or perform
Blueprint ACCEPT / RETURN / HOLD.

`blueprint-pull` is retained only as a deprecated fail-closed compatibility
stub. Historical prompt-state tooling remains available for compatibility but
is not part of the H9 canonical startup path.

`make check`, `make governance-check`, and `make module-validate` remain
network-independent. Live freshness is isolated to
`make coordination-sync-check` and therefore to `make module-start`.
