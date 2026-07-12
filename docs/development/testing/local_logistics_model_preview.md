# Local Logistics Model Preview

## Purpose

The preview demonstrates the complete local Logistics Service
workflow without external provider calls or production writes.

## Workflow examples

The model is built from:

- `examples/workflows/shipment_draft_preview.yaml`;
- `examples/workflows/tracking_request_preview.yaml`;
- `examples/workflows/notification_event_preview.yaml`.

All examples are synthetic, non-canonical and safe for local
development.

## Validation command

```bash
make local-model-examples-check
```

This validates:

- required YAML structure;
- non-canonical ownership;
- preview-only shipment behavior;
- disabled live-provider writes;
- local-only tracking behavior;
- local tracking events;
- local notification payloads;
- consistent references across the three workflow files.

## Human-readable preview

```bash
make logistics-model-preview
```

The preview displays:

- provider reference;
- synthetic recipient;
- shipment-time address ownership;
- shipment draft state;
- tracking flow;
- future display surfaces;
- local repository record totals;
- explicit confirmation that live provider writes are disabled.

## Boundary validation

```bash
make local-model-boundary-check
```

This command checks required implementation and documentation,
scans the local service/storage/preview layers for forbidden
external imports, checks workflow safety flags and rebuilds the
local model in memory.

## Full verification

```bash
make check
make check-report
```

The check report must show the local model examples and local
model boundary rows as successful before completion is prepared.
