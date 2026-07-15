# Check Reporting Recovery

If `make check-report` fails:

1. Read the failed row in the compact summary.
2. Open its matching file under `reports/diagnostics/`.
3. Run the recorded command directly.
4. Correct the module implementation or test failure.
5. Run `make check`.
6. Run `make check-report` again.

Remove generated report artifacts with:

```text
make report-clean
```

Generated reports are evidence only. They are not canonical module
state and must not be used to bypass failed checks.
