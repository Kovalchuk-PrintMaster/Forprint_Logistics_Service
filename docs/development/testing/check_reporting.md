# Check Reporting

Run the compact report:

```text
make check-report
```

Run the full console report:

```text
make check-report-full
```

Disable ANSI colors:

```text
NO_COLOR=1 make check-report
```

The compact report contains a closed-border table, explicit status
text, elapsed time and an overall result.

Full command outputs remain available under:

```text
reports/diagnostics/
```

The inventory includes provider contract validation.
