# Check Reporting Recovery

If `make check-report` or `make check-report-full` fails:

1. Read the failed row and console diagnostics.
2. Run the recorded failing command directly.
3. Correct the implementation, configuration, documentation, or test failure.
4. Run `make check`.
5. Run the read-only report again.

If persistent diagnostics are needed for review, explicitly run:

```text
make check-report-generate
# or
make check-report-full-generate
```

Then inspect the matching generated evidence under:

```text
reports/diagnostics/
```

Remove generated report artifacts with:

```text
make report-clean
```

Generated reports are evidence only. They are not canonical module state and
must not be used to bypass failed checks.
