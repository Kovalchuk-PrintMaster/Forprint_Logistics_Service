# Logistics Service secrets policy

Real provider credentials must never be committed to Git.

Committed configuration may contain only:

- environment variable names;
- safe placeholders;
- disabled adapter settings;
- non-secret provider metadata.

Local credentials belong in an ignored `.env` file or another approved local
secret store.

The presence of credentials must never automatically enable provider writes.

Live provider writes require a future explicitly approved checkpoint with
environment checks, dry-run controls, manual confirmation and audit records.