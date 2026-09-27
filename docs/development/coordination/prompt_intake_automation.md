# Prompt intake automation

## Purpose

Module-side prompt intake must not require repeated manual metadata edits.

## Local prompt lifecycle

`coordination/prompts/received/` stores every approved prompt synchronized
from Blueprint.

`coordination/prompts/active/` stores exactly one prompt currently being
executed by the module.

`coordination/prompts/archived/` stores previous inactive prompt copies.

`coordination/prompts/index.yaml` stores local prompt metadata.

## Standard workflow

```bash
make coordination-sync-check
make blueprint-prompts-check
make blueprint-prompts-sync
make blueprint-prompt-status
make blueprint-prompt
make blueprint-prompt-check
```

`make blueprint-prompts-sync` reads the Blueprint prompt queue and writes only
module-owned coordination state.

`make blueprint-pull` is deprecated and deliberately fails closed. Blueprint
must be changed only from the Blueprint repository.

A `READY_PROMPT` observation does not itself authorize worker execution.
Operator/dispatcher authority remains separate.

## Safety

The automation may read Blueprint files but must write only inside the module
repository.

It must never modify the Blueprint prompt queue or Blueprint repository.
