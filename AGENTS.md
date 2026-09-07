# ForPrint Logistics Service — AI and operator entrypoint

## Purpose

This repository is the Logistics reference pilot. Its root self-knowledge is designed so a
fresh AI worker can understand current implementations, supported compatibility paths,
documentation authority, roadmap position and safe operating boundaries without relying on
chat history.

## Authority order

1. The synchronized Blueprint current release and Prompt Queue under
   `coordination/blueprint_snapshot/` define current cross-module release and prompt state.
2. An explicitly approved task context, Prompt Contract and Acceptance Oracle define the
   exact task when the Blueprint Control Plane later dispatches a worker.
3. This `AGENTS.md` defines stable module workflow and safety rules.
4. Curated module self-knowledge under `coordination/module_memory/` describes significant
   implementations, lineage, document authority and roadmap navigation.
5. Generated inventory and freshness projections are navigation/evidence only.

Never treat historical completion reports, archived prompts or generated indexes as newer
authority than the current release/prompt contract.

## Current execution boundary

The Logistics AI worker is **PAUSED_BY_OPERATOR**.

A ready prompt may be visible in the synchronized Prompt Queue, but readiness alone is not
permission to claim or execute it. Until the central Blueprint Activation Runtime and
Operator Approval Gateway exist, do not create a prompt claim and do not launch an
autonomous worker from this repository.

`module-start` remains the H9 synchronization/readiness workflow. It must not rewrite
curated Module Memory.

## Fresh-context startup

Before implementation work, use:

```bash
make self-knowledge-status
make module-status
make module-memory-check
make document-authority-check
make fresh-context-check
```

If a generated self-knowledge projection is stale, an operator-controlled maintenance step
may run:

```bash
make module-memory-build
```

Then rerun the read-only checks. Do not silently rewrite curated memory to make a check pass.

## Self-knowledge surfaces

Curated:
- `coordination/module_memory/module_memory.yaml`
- `coordination/module_memory/implementation_lineage.yaml`
- `coordination/module_memory/document_authority.yaml`
- `coordination/module_memory/roadmap_state.yaml`

Derived:
- `coordination/module_memory/inventory_index.yaml`
- `coordination/module_memory/current_state.yaml`
- `coordination/module_memory/fresh_context_manifest.yaml`

Curated files explain what the module knows. Derived files prove navigation/current-state
freshness. Derived files are never independent authority.

## Implementation and lineage rules

Track significant implementation surfaces, not every trivial helper.

Preserve explicit distinctions between:
- current implementation;
- supported legacy compatibility;
- specialized current reference;
- historical reference;
- unknown legacy provenance.

Never invent legacy history. Use `UNKNOWN_LEGACY`, low/unknown confidence and review
required when evidence is insufficient.

Do not delete or mass-rename compatibility code merely because a newer implementation
exists. Retirement needs tests, consumers, dependency impact and human review.

## Repository boundaries

Do not:
- write to the Blueprint repository from Logistics;
- mutate another module repository;
- enable production database behavior;
- perform live provider writes;
- mutate Telegram or notification repositories;
- start a daemon/systemd service;
- commit or push without separate operator authorization;
- reset, clean or stash pre-existing worktree state to manufacture cleanliness.

Provider and external-write behavior remains fail-closed unless a separate high-impact
approval explicitly widens it.

## Coordination boundary

The future event listener, launch-request state machine, Operator Approval Gateway,
Worker Adapter and dispatcher belong to the central `forprint_system_blueprint` Control
Plane. They are not owned by Logistics and are not owned by Project Inspector.

This repository owns only its module-local self-knowledge, runtime configuration and task
implementation behavior.

## Completion discipline

A worker completion is module-side evidence, not Blueprint ACCEPT. Completion must report
exact changed paths, validations, lineage/inventory impact, boundaries, resource
observability and unresolved gaps. Manual Blueprint/operator review remains a separate gate.

## Language convention

When writing Ukrainian operator-facing prose, the AI assistant refers to herself in
feminine grammatical forms. Address the human operator in masculine grammatical forms.
