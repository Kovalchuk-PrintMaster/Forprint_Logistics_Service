# Check Reporting

Run the compact **read-only** report:

```text
make check-report
```

Run the full **read-only** console report:

```text
make check-report-full
```

Disable ANSI colors:

```text
NO_COLOR=1 make check-report
```

The read-only commands print status and diagnostics to the console and do not
write report artifacts.

When persistent diagnostic evidence is explicitly needed, use:

```text
make check-report-generate
make check-report-full-generate
```

Those generating variants may write under:

```text
reports/diagnostics/
```

Generated reports are evidence only; they are not canonical module state.
The inventory includes provider contract validation.
