# Check Reporting Architecture

`scripts/diagnostics/run_logistics_checks.py` is the reporting
entrypoint for Logistics Service.

It executes the stable `CHECK_COMMANDS` inventory and creates:

```text
reports/logistics_service_check_report.json
reports/logistics_service_check_report.md
reports/diagnostics/*.log
```

The console output is compact by default. Full command outputs are
written to individual diagnostics files.

`make check-report-full` may print those details for investigation.

Reporting does not replace `make check`; it provides structured
evidence over the same bounded module checks.
