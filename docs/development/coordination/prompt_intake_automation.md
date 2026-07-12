# Prompt intake automation

## Purpose

Module-side prompt intake must not require repeated manual metadata edits.

## Local prompt lifecycle

`coordination/prompts/received/` stores every approved prompt synchronized
from Blueprint.

`coordination/prompts/active/` stores exactly one prompt currently being
executed by the module.

`coordination/prompts/archived/` stores previous inactive prompt copies.

`coordination/prompts/index.yaml` stores the local prompt metadata and
identifies the current active prompt.

## Standard workflow

```bash
make blueprint-pull
make blueprint-prompts-check
make blueprint-prompts-sync
make blueprint-prompt-status
make blueprint-prompt
make blueprint-prompt-check
```

`make blueprint-prompts-sync` reads the Blueprint prompt queue index,
synchronizes approved prompt files, selects the next executable prompt,
updates local coordination metadata and activates the prompt.

## Safety

The automation reads Blueprint files but writes only inside the module
repository.

It must never modify the Blueprint prompt queue or Blueprint repository.
