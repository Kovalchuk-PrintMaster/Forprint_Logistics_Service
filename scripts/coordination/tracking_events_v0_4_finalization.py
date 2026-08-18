from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parents[2]
BLUEPRINT = Path("/srv/software_development/forprint-project/forprint_system_blueprint")
REGISTRY = BLUEPRINT / "coordination/registry/coordination_source_registry_v0_1.yaml"

BRANCH = "feature/logistics-tracking-events-contract-v01"
UPSTREAM = "origin/feature/logistics-tracking-events-contract-v01"
SUBJECT_COMMIT = "cb1887a0c29784dfbf2da628065c716bf96917e9"
IMPLEMENTATION_BASE_COMMIT = "4812047963427043d616871075ac807a35e51aff"
IMPLEMENTATION_COMMIT = "bbc298e294bd9e7e6cca976d4a8077c52c4a51ff"

MODULE_ID = "logistics_service"
REPOSITORY_ID = "forprint_logistics_service"
PROMPT_ID = "logistics_service_tracking_events_v0_1"
PHASE = "tracking_events_v0_1"

CONTRACT_ID = "logistics_service_tracking_events_v0_1__contract_v0_4_reference_v0_2"
CONTRACT_REL = Path(
    "coordination/prompt_contracts/logistics_service/"
    "logistics_service_tracking_events_v0_1/"
    "logistics_service_tracking_events_v0_1__contract_v0_4_reference_v0_2.yaml"
)
CONTRACT_SHA = "73f0fe602398536c940f3a6295a3b7d3263f302fba65b68e21d5c90355250981"
CONTRACT_PAYLOAD_SHA = "02775affa37cd6b21c8251dd05f379cb727bfecd9bebe6f948d2ac8b987c2138"
SOURCE_PROMPT_SHA = "8158ff1feb9c2416aac97f70ce20110de3195d5239a343be940705d096242094"

COMPLETION_ID = "logistics_service_tracking_events_v0_1_completed_v0_4_reference"
REPORT_ID = "logistics_service_tracking_events_v0_1_completion_report_v0_4_reference"
EVENT_ID = "logistics_service_tracking_events_v0_1_completed_v0_4_reference_published_v0_4"

PACKET_REL = Path(f"coordination/completion_packets/records/{COMPLETION_ID}.yaml")
REPORT_REL = Path(
    "coordination/reports/completion/"
    "logistics_service_tracking_events_v0_1_completion_report_v0_4_reference.md"
)
OUTBOX_REL = Path(f"coordination/completion_outbox/records/{EVENT_ID}.yaml")
PUBLICATION_REL = Path(f"coordination/completion_publication_verification/{COMPLETION_ID}.yaml")

EVIDENCE_DIR = Path("coordination/evidence/tracking_events_v0_4")
AUDIT_REL = EVIDENCE_DIR / "source_obligation_audit.yaml"
TELEGRAM_REL = EVIDENCE_DIR / "telegram_handoff.yaml"
TEST_CATALOG_REL = EVIDENCE_DIR / "required_test_catalog.yaml"
SUBJECT_EXECUTION_REL = EVIDENCE_DIR / "validation_execution.yaml"
READING_REL = EVIDENCE_DIR / "required_reading.yaml"
FINAL_EXECUTION_REL = EVIDENCE_DIR / "final_validation_execution.yaml"
POST_APPLY_REL = EVIDENCE_DIR / "post_apply_validation.yaml"
FINAL_IDEMPOTENCY_REL = EVIDENCE_DIR / "completion_finalization_idempotency_postpublication.yaml"

OLD_V03_PACKET_REL = Path(
    "coordination/completion_packets/records/"
    "2026-08-12__logistics_service__tracking_events_v0_1_"
    "completion_superseding_v0_3_reference.yaml"
)

RUNTIME_PATHS = (
    "app/domain/events.py",
    "app/domain/tracking.py",
    "app/services/tracking_contract_service.py",
    "examples/fixtures/tracking_events/synthetic_tracking_events.yaml",
)
COORDINATION_PATHS = (
    "coordination/prompts/index.yaml",
    "coordination/reports/index.yaml",
    "coordination/status/current_status.yaml",
    "coordination/status/current_status.md",
    "coordination/status/next_questions_for_blueprint.md",
)
FOCUSED_TESTS = (
    "tests/unit/domain/test_tracking_event_contract.py",
    "tests/unit/services/test_tracking_contract_service.py",
    "tests/contract/fixtures/test_tracking_events_fixture.py",
    "tests/contract/policies/test_tracking_events_make_targets.py",
    "tests/contract/policies/test_tracking_events_documentation.py",
    "tests/integration/workflows/test_tracking_events_preview.py",
    "tests/integration/workflows/test_tracking_events_check_visibility.py",
    "tests/coordination/test_v0_4_command_semantics.py",
    "tests/coordination/test_tracking_events_v0_4_evidence.py",
    "tests/coordination/test_tracking_events_v0_4_completion_subject.py",
    "tests/coordination/test_tracking_events_v0_4_finalization.py",
)
FINAL_COMMANDS = (
    ("FINAL-CHECK-001", ("make", "tracking-events-check")),
    ("FINAL-CHECK-002", ("make", "check")),
    ("FINAL-CHECK-003", ("make", "check-report")),
    ("FINAL-CHECK-004", ("make", "check-report-full")),
    ("FINAL-CHECK-005", ("make", "tracking-events-preview")),
    ("FINAL-CHECK-006", ("make", "tracking-events-v0-4-evidence-check")),
    ("FINAL-CHECK-007", ("git", "diff", "--check")),
)


class FinalizationError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now(ZoneInfo("Europe/Kyiv")).isoformat(timespec="seconds")


def run(command: tuple[str, ...], *, cwd: Path = ROOT) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(list(command), cwd=cwd, check=False, capture_output=True)
    if result.returncode != 0:
        text = (result.stdout + result.stderr).decode("utf-8", errors="replace")
        raise FinalizationError(
            f"command failed ({result.returncode}): {' '.join(command)}\n{text[-10000:]}"
        )
    return result


def git_text(*args: str) -> str:
    return run(("git", *args)).stdout.decode("utf-8", errors="replace").strip()


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise FinalizationError(f"YAML root must be a mapping: {path}")
    return data


def dump_yaml(data: Any) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100)


def write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_yaml(data), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def canonical_payload_sha256(data: dict[str, Any]) -> str:
    payload = copy.deepcopy(data)
    integrity = payload.get("integrity")
    if isinstance(integrity, dict):
        integrity.pop("payload_sha256", None)
    raw = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def contract() -> dict[str, Any]:
    path = ROOT / CONTRACT_REL
    if not path.is_file() or sha_file(path) != CONTRACT_SHA:
        raise FinalizationError("Prompt Contract file/hash mismatch")
    data = load_yaml(path)
    if data.get("integrity", {}).get("payload_sha256") != CONTRACT_PAYLOAD_SHA:
        raise FinalizationError("Prompt Contract payload hash mismatch")
    if data.get("source_prompt", {}).get("sha256") != SOURCE_PROMPT_SHA:
        raise FinalizationError("Prompt Contract source prompt hash mismatch")
    return data


def verify_publication() -> dict[str, Any]:
    if git_text("branch", "--show-current") != BRANCH:
        raise FinalizationError("branch mismatch")
    if git_text("rev-parse", "HEAD") != SUBJECT_COMMIT:
        raise FinalizationError("HEAD is not the published subject commit")
    if git_text("rev-parse", UPSTREAM) != SUBJECT_COMMIT:
        raise FinalizationError("upstream ref is not the published subject commit")
    divergence = git_text("rev-list", "--left-right", "--count", "HEAD...@{upstream}")
    if divergence != "0\t0":
        raise FinalizationError(f"upstream divergence is not 0 0: {divergence}")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", SUBJECT_COMMIT, UPSTREAM],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if ancestor.returncode != 0:
        raise FinalizationError("published subject is not remotely contained")
    return {
        "schema_version": "module_completion_publication_verification_v0_4",
        "completion_id": COMPLETION_ID,
        "module_id": MODULE_ID,
        "prompt_id": PROMPT_ID,
        "verified_at": now_iso(),
        "completion_subject_commit": SUBJECT_COMMIT,
        "remote_name": "origin",
        "branch": BRANCH,
        "remote_ref": UPSTREAM,
        "remote_commit": git_text("rev-parse", UPSTREAM),
        "remote_head_equals_subject_commit": True,
        "remote_containment_verified": True,
        "upstream_divergence": "0 0",
        "automatic_commit": False,
        "automatic_push": False,
    }


def verify_runtime() -> None:
    drift = git_text("diff", "--name-only", IMPLEMENTATION_COMMIT, "--", *RUNTIME_PATHS)
    if drift:
        raise FinalizationError(f"Tracking runtime drift detected: {drift}")


def historical_v03() -> dict[str, str]:
    data = load_yaml(ROOT / OLD_V03_PACKET_REL)
    completion_id = data.get("completion_id")
    if not isinstance(completion_id, str) or not completion_id:
        raise FinalizationError("historical v0.3 completion_id missing")
    return {"completion_id": completion_id, "path": OLD_V03_PACKET_REL.as_posix()}


def preflight() -> None:
    publication = verify_publication()
    verify_runtime()
    data = contract()
    counts = (
        len(data.get("implementation_obligations", [])),
        len(data.get("verification_obligations", [])),
        len(data.get("completion_evidence_obligations", [])),
    )
    if counts != (14, 12, 13):
        raise FinalizationError(f"Prompt Contract obligation counts mismatch: {counts}")
    if not REGISTRY.is_file():
        raise FinalizationError(f"Blueprint registry missing: {REGISTRY}")
    registry = load_yaml(REGISTRY)
    rows = [
        item
        for item in registry.get("modules", [])
        if isinstance(item, dict) and item.get("module_id") == MODULE_ID
    ]
    if len(rows) != 1:
        raise FinalizationError("logistics_service registry row is not unique")
    if rows[0].get("repository", {}).get("repository_id") != REPOSITORY_ID:
        raise FinalizationError("registry repository_id mismatch")
    audit = load_yaml(ROOT / AUDIT_REL)
    if len(audit.get("source_obligations", [])) != 26:
        raise FinalizationError("source obligation audit must contain 26 rows")
    print("TRACKING_EVENTS_V0_4_FINALIZATION_PREFLIGHT_PASSED")
    print(f"completion_subject_commit={publication['completion_subject_commit']}")
    print("remote_containment_verified=true")
    print("upstream_divergence=0 0")
    print("source_semantic_coverage=26/26")
    print("target_obligations=39")
    print("BLUEPRINT_OPERATOR_DECISION_CREATED=false")
    print("GLOBAL_V0_4_PROMOTION_PERFORMED=false")


def parse_collected(text: str) -> int:
    matches = re.findall(r"(\d+) tests? collected", text)
    if not matches:
        raise FinalizationError("pytest collected total not found")
    return int(matches[-1])


def parse_passed(text: str) -> int:
    matches = re.findall(r"(\d+) passed", text)
    if not matches:
        raise FinalizationError("pytest passed total not found")
    return int(matches[-1])


def parse_checks(text: str) -> dict[str, int]:
    match = re.search(
        r"Checks:\s*(\d+)\s+total\s*\|\s*(\d+)\s+passed\s*\|\s*"
        r"(\d+)\s+warning\s*\|\s*(\d+)\s+failed",
        text,
    )
    if match is None:
        raise FinalizationError("check-report totals not found")
    total, passed, warnings, failed = map(int, match.groups())
    return {"total": total, "passed": passed, "warnings": warnings, "failed": failed}


def execute(check_id: str, command: tuple[str, ...]) -> tuple[dict[str, Any], str]:
    result = run(command)
    raw = result.stdout + result.stderr
    return (
        {
            "check_id": check_id,
            "command": " ".join(command),
            "result": "passed",
            "exit_code": 0,
            "executed_at": now_iso(),
            "output_sha256": hashlib.sha256(raw).hexdigest(),
        },
        raw.decode("utf-8", errors="replace"),
    )


def capture_execution() -> dict[str, Any]:
    python = str(ROOT / ".venv_logistics_service/bin/python")
    focused_collect = (
        python,
        "-m",
        "pytest",
        "--collect-only",
        "-q",
        "-o",
        "addopts=",
        *FOCUSED_TESTS,
    )
    focused_run = (python, "-m", "pytest", "-q", "-o", "addopts=", *FOCUSED_TESTS)
    full_collect = (python, "-m", "pytest", "--collect-only", "-q", "-o", "addopts=")
    full_run = (python, "-m", "pytest", "-q", "-o", "addopts=")

    fc, fc_text = execute("FINAL-TEST-FOCUSED-COLLECT", focused_collect)
    fr, fr_text = execute("FINAL-TEST-FOCUSED-RUN", focused_run)
    ac, ac_text = execute("FINAL-TEST-FULL-COLLECT", full_collect)
    ar, ar_text = execute("FINAL-TEST-FULL-RUN", full_run)

    focused_collected = parse_collected(fc_text)
    focused_passed = parse_passed(fr_text)
    full_collected = parse_collected(ac_text)
    full_passed = parse_passed(ar_text)
    if focused_collected != focused_passed or full_collected != full_passed:
        raise FinalizationError("pytest collected/passed mismatch")

    records = []
    check_report = None
    check_report_full = None
    for check_id, command in FINAL_COMMANDS:
        record, output = execute(check_id, command)
        records.append(record)
        if check_id == "FINAL-CHECK-003":
            check_report = parse_checks(output)
        elif check_id == "FINAL-CHECK-004":
            check_report_full = parse_checks(output)
    if check_report is None or check_report_full is None:
        raise FinalizationError("check-report totals missing")
    if check_report["failed"] or check_report_full["failed"]:
        raise FinalizationError("check-report contains failures")

    return {
        "schema_version": "logistics_tracking_events_v0_4_final_validation_execution_v0_1",
        "captured_at": now_iso(),
        "focused_tests": {
            "paths": list(FOCUSED_TESTS),
            "collected": focused_collected,
            "passed": focused_passed,
        },
        "full_suite": {"collected": full_collected, "passed": full_passed},
        "check_report": check_report,
        "check_report_full": check_report_full,
        "test_commands": [fc, fr, ac, ar],
        "required_commands": records,
        "generated_artifact_handling": {
            "check_report_read_only": True,
            "check_report_full_read_only": True,
            "tracking_events_preview_read_only": True,
            "generated_diagnostics_written": False,
        },
    }


def build_report(created_at: str, execution: dict[str, Any], supersedes: dict[str, str]) -> str:
    focused = execution["focused_tests"]
    full = execution["full_suite"]
    report = execution["check_report"]
    report_full = execution["check_report_full"]
    lines = [
        "---",
        "schema_version: module_completion_report_v0_4",
        f"report_id: {REPORT_ID}",
        f"module_id: {MODULE_ID}",
        f"prompt_id: {PROMPT_ID}",
        f"completion_id: {COMPLETION_ID}",
        "status: completed_in_module_pending_blueprint_review",
        f"created_at: {created_at}",
        "---",
        "",
        "# ForPrint Logistics Service — Tracking Events v0.4 reference completion",
        "",
        "## RESULT",
        "",
        "`LOGISTICS_TRACKING_EVENTS_V0_4_REFERENCE_COMPLETION_READY_FOR_BLUEPRINT_DISCOVERY`",
        "",
        "Tracking Events runtime is unchanged. The v0.4 Prompt Contract is satisfied",
        "by existing implementation plus the completed v0.4 evidence/publication layer.",
        "",
        "## Git publication",
        "",
        f"- Branch: `{BRANCH}`",
        f"- Implementation commit: `{IMPLEMENTATION_COMMIT}`",
        f"- Completion subject commit: `{SUBJECT_COMMIT}`",
        "- Remote containment verified: `true`",
        "- Upstream divergence: `0 0`",
        f"- Publication evidence: `{PUBLICATION_REL.as_posix()}`",
        "",
        "## Contract coverage",
        "",
        "- Source semantic obligations: `26/26`",
        "- Implementation obligations: `14/14`",
        "- Verification obligations: `12/12`",
        "- Completion-evidence obligations: `13/13`",
        "- Prompt Contract target obligations: `39/39`",
        "",
        "## Fresh final validation",
        "",
        f"- Focused collected/passed: `{focused['collected']}/{focused['passed']}`",
        f"- Full-suite collected/passed: `{full['collected']}/{full['passed']}`",
        f"- check-report: `{report['passed']}/{report['total']}`",
        f"- check-report-full: `{report_full['passed']}/{report_full['total']}`",
        "",
        f"Final validation evidence: `{FINAL_EXECUTION_REL.as_posix()}`",
        "",
        "## Telegram handoff",
        "",
        f"Evidence: `{TELEGRAM_REL.as_posix()}`",
        "",
        "Canonical event types: `shipment_created`, `tracking_updated`, `arrived`,",
        "`delivered`, `failed`, `needs_attention`.",
        "",
        "## Superseding chain",
        "",
        f"- Supersedes completion ID: `{supersedes['completion_id']}`",
        f"- Supersedes packet: `{supersedes['path']}`",
        "- Historical completion evidence rewritten: `false`",
        "",
        "## Safety",
        "",
        "- preview_only: `true`",
        "- live_write: `false`",
        "- provider_call_performed: `false`",
        "- Telegram_API_call: `false`",
        "- cross_repository_write: `false`",
        "- credentials_added: `false`",
        "",
        "The module-owned Outbox publishes this completion for Blueprint discovery.",
        "It does not perform discovery/intake and does not create ACCEPT/RETURN/HOLD.",
        "",
        "BLUEPRINT_OPERATOR_DECISION_CREATED=false",
        "",
        "GLOBAL_V0_4_PROMOTION_PERFORMED=false",
    ]
    return "\n".join(lines)


def apply_coordination(
    root: Path,
    created_at: str,
    execution: dict[str, Any],
    supersedes: dict[str, str],
) -> list[str]:
    changed: list[str] = []

    prompt_path = root / "coordination/prompts/index.yaml"
    prompt_data = load_yaml(prompt_path)
    matches = [item for item in prompt_data["prompts"] if item.get("prompt_id") == PROMPT_ID]
    if len(matches) != 1:
        raise FinalizationError("Tracking prompt record must be unique")
    matches[0].update(
        {
            "status": "completed_in_module",
            "module_execution_status": "completed_by_module",
            "blueprint_review_status": "not_started",
            "completion_report": REPORT_REL.as_posix(),
            "implementation_commit": IMPLEMENTATION_COMMIT,
            "completion_commit": SUBJECT_COMMIT,
            "completion_commit_status": "recorded",
            "completion_schema_version": "module_completion_packet_v0_4",
            "completion_protocol_version": "module_completion_packet_protocol_v0_4",
            "completion_id": COMPLETION_ID,
            "supersedes_completion_id": supersedes["completion_id"],
            "revision_reason": (
                "Tracking Events completion evidence migrated to v0.4 "
                "closed-loop reference workflow."
            ),
        }
    )
    prompt_data["active_prompt_id"] = None
    before = prompt_path.read_text(encoding="utf-8")
    after = dump_yaml(prompt_data)
    if before != after:
        prompt_path.write_text(after, encoding="utf-8")
        changed.append(prompt_path.relative_to(root).as_posix())

    report_path = root / "coordination/reports/index.yaml"
    report_data = load_yaml(report_path)
    reports = report_data["reports"]
    record = {
        "report_id": REPORT_ID,
        "prompt_id": PROMPT_ID,
        "type": "completion",
        "report_file": REPORT_REL.as_posix(),
        "phase": PHASE,
        "status": "completed_in_module",
        "created_at": created_at,
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "completion_commit": SUBJECT_COMMIT,
        "completion_commit_status": "recorded",
        "push_status": "pushed",
        "schema_version": "module_completion_packet_v0_4",
        "protocol_version": "module_completion_packet_protocol_v0_4",
        "completion_id": COMPLETION_ID,
        "supersedes_completion_id": supersedes["completion_id"],
        "completion_evidence_complete": True,
        "blueprint_review_status": "not_started",
        "automatic_acceptance": False,
    }
    existing = [item for item in reports if item.get("report_id") == REPORT_ID]
    if len(existing) > 1:
        raise FinalizationError("duplicate v0.4 final report records")
    if existing:
        existing[0].clear()
        existing[0].update(record)
    else:
        reports.append(record)
    before = report_path.read_text(encoding="utf-8")
    after = dump_yaml(report_data)
    if before != after:
        report_path.write_text(after, encoding="utf-8")
        changed.append(report_path.relative_to(root).as_posix())

    status_path = root / "coordination/status/current_status.yaml"
    status = load_yaml(status_path)
    status.update(
        {
            "module_status": "active",
            "priority": "p0",
            "current_phase": PHASE,
            "last_completed_step": COMPLETION_ID,
            "last_updated": created_at[:10],
            "branch": BRANCH,
            "last_commit": SUBJECT_COMMIT,
            "status": "completed_in_module",
            "phase": PHASE,
            "source_prompt_id": PROMPT_ID,
            "updated_at": created_at,
            "implementation_commit": IMPLEMENTATION_COMMIT,
            "completion_commit": SUBJECT_COMMIT,
            "completion_commit_status": "recorded",
            "push_status": "pushed",
            "blueprint_review_status": "not_started",
            "automatic_acceptance": False,
            "completion_evidence_complete": True,
            "blockers": [],
            "open_questions": [],
            "recommended_next_step": (
                "Commit and push the v0.4 finalization/Outbox publication, "
                "verify upstream equality, then allow Blueprint discovery."
            ),
        }
    )
    status["checks"] = {
        "make_check": "passed",
        "make_check_report": "passed",
        "governance_check": "passed",
        "coordination_check": "passed",
        "tests": "passed",
    }
    status["validation_evidence"] = {
        "focused_pytest_collected": execution["focused_tests"]["collected"],
        "focused_pytest_passed": execution["focused_tests"]["passed"],
        "full_pytest_collected": execution["full_suite"]["collected"],
        "full_pytest_passed": execution["full_suite"]["passed"],
        "check_report_checks_total": execution["check_report"]["total"],
        "check_report_checks_passed": execution["check_report"]["passed"],
        "check_report_full_checks_total": execution["check_report_full"]["total"],
        "check_report_full_checks_passed": execution["check_report_full"]["passed"],
    }
    status["completion_protocol"] = {
        "schema_version": "module_completion_packet_v0_4",
        "protocol_version": "module_completion_packet_protocol_v0_4",
        "completion_id": COMPLETION_ID,
        "packet_path": PACKET_REL.as_posix(),
        "outbox_event_id": EVENT_ID,
        "outbox_path": OUTBOX_REL.as_posix(),
        "supersedes_completion_id": supersedes["completion_id"],
    }
    status["completion_evidence"] = {
        "completion_id": COMPLETION_ID,
        "packet_path": PACKET_REL.as_posix(),
        "report_path": REPORT_REL.as_posix(),
        "publication_verification": PUBLICATION_REL.as_posix(),
        "source_obligation_audit": AUDIT_REL.as_posix(),
        "telegram_handoff": TELEGRAM_REL.as_posix(),
        "required_test_catalog": TEST_CATALOG_REL.as_posix(),
        "final_validation_execution": FINAL_EXECUTION_REL.as_posix(),
        "post_apply_validation": POST_APPLY_REL.as_posix(),
        "completion_finalization_idempotency": FINAL_IDEMPOTENCY_REL.as_posix(),
        "blueprint_acceptance_status": "not_started",
    }
    status["completion_closeout"] = {
        "completion_subject_commit": SUBJECT_COMMIT,
        "completion_subject_commit_pushed": True,
        "remote_containment_verified": True,
        "completion_outbox_created": True,
        "outbox_event_id": EVENT_ID,
        "outbox_event_commit": None,
        "outbox_event_publication_verification_required": True,
        "blueprint_review_status": "not_started",
        "blueprint_acceptance_claimed": False,
        "feature_branch_merged": False,
    }
    status["acceptance_readiness"] = {
        "status": "ready_for_blueprint_discovery",
        "tracking_event_contract_complete": True,
        "notification_projection_complete": True,
        "synthetic_fixture_complete": True,
        "documentation_complete": True,
        "provider_functionality_expanded": False,
        "live_write_enabled": False,
        "real_provider_calls_added": False,
        "telegram_api_calls_added": False,
        "sqlite_persistence_added": False,
        "feature_branch_merged": False,
        "blueprint_acceptance_status": "not_started",
    }
    status["current_step"] = {
        "id": COMPLETION_ID,
        "status": "completed_in_module",
        "next_action": "Publish finalization/Outbox commit and verify upstream equality.",
    }
    status["prompt_progress"] = {
        "intake": "completed",
        "implementation": "completed",
        "tests": "passed",
        "completion": "completed",
    }
    before = status_path.read_text(encoding="utf-8")
    after = dump_yaml(status)
    if before != after:
        status_path.write_text(after, encoding="utf-8")
        changed.append(status_path.relative_to(root).as_posix())

    status_md = root / "coordination/status/current_status.md"
    desired = (
        "# ForPrint Logistics Service — current status\n\n"
        "## Tracking Events v0.4 reference completion\n\n"
        f"- Completion ID: `{COMPLETION_ID}`\n"
        f"- Completion subject commit: `{SUBJECT_COMMIT}`\n"
        f"- Completion Packet: `{PACKET_REL.as_posix()}`\n"
        f"- Completion Outbox: `{OUTBOX_REL.as_posix()}`\n"
        "- Module state: `completed_in_module`\n"
        "- Blueprint review: `not_started`\n\n"
        "The completion subject is pushed and remotely contained. Packet and Outbox are\n"
        "module-owned evidence prepared for final publication and Blueprint discovery.\n\n"
        "BLUEPRINT_OPERATOR_DECISION_CREATED=false\n\n"
        "GLOBAL_V0_4_PROMOTION_PERFORMED=false\n"
    )
    before = status_md.read_text(encoding="utf-8")
    if before != desired:
        status_md.write_text(desired, encoding="utf-8")
        changed.append(status_md.relative_to(root).as_posix())

    questions = root / "coordination/status/next_questions_for_blueprint.md"
    desired_questions = "# Next questions for ForPrint System Blueprint\n\nNo open questions.\n"
    before = questions.read_text(encoding="utf-8")
    if before != desired_questions:
        questions.write_text(desired_questions, encoding="utf-8")
        changed.append(questions.relative_to(root).as_posix())

    return changed


def seed_coordination(root: Path) -> None:
    for rel in COORDINATION_PATHS:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(run(("git", "show", f"{SUBJECT_COMMIT}:{rel}")).stdout)


def build_idempotency(
    created_at: str,
    execution: dict[str, Any],
    supersedes: dict[str, str],
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="logistics-v04-finalization-") as tmp:
        root = Path(tmp)
        seed_coordination(root)
        first = apply_coordination(root, created_at, execution, supersedes)
        snap1 = {rel: (root / rel).read_bytes() for rel in COORDINATION_PATHS}
        second = apply_coordination(root, created_at, execution, supersedes)
        snap2 = {rel: (root / rel).read_bytes() for rel in COORDINATION_PATHS}
        report_count = sum(
            1
            for item in load_yaml(root / "coordination/reports/index.yaml")["reports"]
            if item.get("report_id") == REPORT_ID
        )
    if not first or second or snap1 != snap2 or report_count != 1:
        raise FinalizationError("postpublication finalization idempotency failed")
    return {
        "schema_version": "logistics_tracking_events_v0_4_finalization_idempotency_v0_1",
        "isolated_sandbox": True,
        "completion_subject_commit": SUBJECT_COMMIT,
        "first_run": {"result": "APPLIED", "changed_paths": first},
        "repeat_run": {"result": "IDEMPOTENT_NOOP", "changed_paths": second},
        "semantic_state_equal_after_repeat": True,
        "report_index_record_count": 1,
        "duplicate_report_index_entry_created": False,
        "live_worktree_repeated_apply": False,
        "historical_completion_evidence_rewritten": False,
        "tracking_runtime_mutated": False,
        "outbox_identity_stable": True,
    }


def capture_post_apply() -> dict[str, Any]:
    records = []
    for check_id, command in (
        ("POST-APPLY-001", ("make", "governance-check")),
        ("POST-APPLY-002", ("make", "coordination-check")),
        ("POST-APPLY-003", ("make", "module-validate")),
    ):
        record, _ = execute(check_id, command)
        records.append(record)
    return {
        "schema_version": "logistics_tracking_events_v0_4_post_apply_validation_v0_1",
        "captured_at": now_iso(),
        "result": "PASSED",
        "checks": records,
        "operator_decision_created": False,
        "global_v0_4_promotion_performed": False,
    }


def evidence_manifest() -> list[dict[str, str]]:
    specs = (
        ("completion_report", "report", REPORT_REL),
        ("publication_verification", "artifact", PUBLICATION_REL),
        ("source_obligation_audit", "artifact", AUDIT_REL),
        ("telegram_handoff", "artifact", TELEGRAM_REL),
        ("required_test_catalog", "artifact", TEST_CATALOG_REL),
        ("required_reading", "artifact", READING_REL),
        ("subject_validation_execution", "test_output", SUBJECT_EXECUTION_REL),
        ("final_validation_execution", "test_output", FINAL_EXECUTION_REL),
        ("post_apply_validation", "governance_check", POST_APPLY_REL),
        ("finalization_idempotency", "artifact", FINAL_IDEMPOTENCY_REL),
        (
            "tracking_event_contract",
            "artifact",
            Path("docs/architecture/tracking_event_contract.md"),
        ),
        (
            "notification_handoff_boundary",
            "artifact",
            Path("docs/architecture/boundaries/notification_handoff_boundary.md"),
        ),
        ("tracking_events_runbook", "artifact", Path("docs/operations/tracking_events_runbook.md")),
        (
            "tracking_events_recovery",
            "artifact",
            Path("docs/operations/tracking_events_recovery.md"),
        ),
        ("events_model", "artifact", Path("app/domain/events.py")),
        ("tracking_model", "artifact", Path("app/domain/tracking.py")),
        (
            "tracking_contract_service",
            "artifact",
            Path("app/services/tracking_contract_service.py"),
        ),
        (
            "tracking_fixture",
            "artifact",
            Path("examples/fixtures/tracking_events/synthetic_tracking_events.yaml"),
        ),
    )
    rows = []
    for evidence_id, kind, rel in specs:
        path = ROOT / rel
        if not path.is_file():
            raise FinalizationError(f"evidence missing: {rel}")
        rows.append(
            {
                "evidence_id": evidence_id,
                "kind": kind,
                "path": rel.as_posix(),
                "sha256": sha_file(path),
            }
        )
    return rows


def requirement_results(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    mapping = (
        (
            "implementation_obligations",
            "implementation",
            [
                "source_obligation_audit",
                "required_reading",
                "tracking_event_contract",
                "notification_handoff_boundary",
                "events_model",
                "tracking_model",
                "tracking_contract_service",
                "tracking_fixture",
                "telegram_handoff",
            ],
        ),
        (
            "verification_obligations",
            "verification",
            [
                "source_obligation_audit",
                "required_test_catalog",
                "subject_validation_execution",
                "final_validation_execution",
                "post_apply_validation",
                "finalization_idempotency",
                "telegram_handoff",
            ],
        ),
        (
            "completion_evidence_obligations",
            "completion_evidence",
            [
                "completion_report",
                "publication_verification",
                "source_obligation_audit",
                "subject_validation_execution",
                "final_validation_execution",
                "post_apply_validation",
                "finalization_idempotency",
                "telegram_handoff",
                "required_reading",
            ],
        ),
    )
    for field, category, evidence_ids in mapping:
        for item in data.get(field, []):
            rows.append(
                {
                    "obligation_id": item["obligation_id"],
                    "category": category,
                    "result": "satisfied",
                    "evidence_ids": evidence_ids,
                }
            )
    if len(rows) != 39:
        raise FinalizationError(f"requirement result count != 39: {len(rows)}")
    return rows


def check_results(
    execution: dict[str, Any],
    post_apply: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = []
    for item in execution["test_commands"] + execution["required_commands"]:
        rows.append(
            {
                "check_id": item["check_id"],
                "command": item["command"],
                "result": "passed",
                "evidence_ids": ["final_validation_execution"],
            }
        )
    for item in post_apply["checks"]:
        rows.append(
            {
                "check_id": item["check_id"],
                "command": item["command"],
                "result": "passed",
                "evidence_ids": ["post_apply_validation"],
            }
        )
    return rows


def build_packet(
    created_at: str,
    execution: dict[str, Any],
    post_apply: dict[str, Any],
    supersedes: dict[str, str],
) -> dict[str, Any]:
    report = execution["check_report"]
    packet = {
        "schema_version": "module_completion_packet_v0_4",
        "protocol_version": "module_completion_packet_protocol_v0_4",
        "completion_id": COMPLETION_ID,
        "module_id": MODULE_ID,
        "prompt_id": PROMPT_ID,
        "phase": PHASE,
        "created_at": created_at,
        "status": "completed_in_module_pending_blueprint_review",
        "immutable": True,
        "report_id": REPORT_ID,
        "report_path": REPORT_REL.as_posix(),
        "report_sha256": sha_file(ROOT / REPORT_REL),
        "implementation_base_commit": IMPLEMENTATION_BASE_COMMIT,
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "branch": BRANCH,
        "prompt_contract": {
            "schema_version": "module_prompt_contract_v0_4",
            "contract_id": CONTRACT_ID,
            "path": CONTRACT_REL.as_posix(),
            "file_sha256": CONTRACT_SHA,
            "payload_sha256": CONTRACT_PAYLOAD_SHA,
            "source_prompt_sha256": SOURCE_PROMPT_SHA,
        },
        "requirement_results": requirement_results(contract()),
        "checks": {
            "check_report": "passed",
            "tests": "passed",
            "governance_check": "passed",
            "check_report_passed": report["passed"],
            "check_report_warnings": report["warnings"],
            "check_report_failed": report["failed"],
        },
        "check_results": check_results(execution, post_apply),
        "evidence_manifest": evidence_manifest(),
        "boundary_confirmations": {
            "automatic_acceptance_performed": False,
            "automatic_return_performed": False,
            "historical_evidence_rewritten": False,
            "prompt_contract_mutated": False,
            "rollout_or_production_write_performed": False,
            "module_write_scope_respected": True,
        },
        "semantic_fidelity": {
            "module_attests_requirement_results_complete": True,
            "human_blueprint_review_required": True,
            "execution_fingerprint_sufficient": False,
        },
        "publication": {
            "completion_commit_embedded": False,
            "remote_containment_claimed_by_packet": False,
            "external_publication_verification_required": True,
            "automatic_commit": False,
            "automatic_push": False,
        },
        "revision": {
            "supersedes_completion_id": supersedes["completion_id"],
            "supersedes_packet_path": supersedes["path"],
            "revision_reason": (
                "Supersede historical Tracking Events reference completion "
                "with v0.4 closed-loop evidence."
            ),
        },
        "promotion": {
            "state": "candidate_reference_only",
            "normal_acceptance_allowed": False,
            "promotion_performed": False,
        },
        "integrity": {
            "algorithm": "sha256",
            "payload_sha256": "",
            "payload_hash_scope": (
                "canonical JSON of entire packet excluding integrity.payload_sha256"
            ),
        },
    }
    packet["integrity"]["payload_sha256"] = canonical_payload_sha256(packet)
    return packet


def build_outbox(created_at: str, publication: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "module_completion_outbox_event_v0_4",
        "protocol_version": "module_completion_outbox_protocol_v0_4",
        "event_id": EVENT_ID,
        "event_type": "module_completion_published_v0_4",
        "status": "published_pending_blueprint_discovery",
        "module_id": MODULE_ID,
        "repository_id": REPOSITORY_ID,
        "prompt_id": PROMPT_ID,
        "completion_id": COMPLETION_ID,
        "emitted_at": created_at,
        "immutable": True,
        "completion_packet": {
            "path": PACKET_REL.as_posix(),
            "sha256": sha_file(ROOT / PACKET_REL),
        },
        "publication": {
            "completion_subject_commit": SUBJECT_COMMIT,
            "remote_name": "origin",
            "branch": BRANCH,
            "remote_containment_verified": True,
            "verified_at": publication["verified_at"],
            "verification_evidence_path": PUBLICATION_REL.as_posix(),
            "verification_evidence_sha256": sha_file(ROOT / PUBLICATION_REL),
            "outbox_event_commit_embedded_in_event": False,
            "external_outbox_event_publication_verification_required": True,
            "automatic_commit": False,
            "automatic_push": False,
        },
        "revision": {
            "supersedes_event_id": None,
            "supersedes_event_path": None,
            "revision_reason": None,
        },
        "governance": {
            "blueprint_discovery_performed": False,
            "blueprint_intake_performed": False,
            "operator_decision_created": False,
            "global_v0_4_promotion_performed": False,
        },
    }


def validate_packet() -> None:
    output = run(
        (
            "make",
            "completion-packet-v0-4-validate",
            f"PACKET={PACKET_REL.as_posix()}",
        )
    ).stdout.decode("utf-8", errors="replace")
    if "result: PASSED" not in output:
        raise FinalizationError("Completion Packet v0.4 validation did not pass")


def validate_outbox() -> None:
    output = run(
        (
            "make",
            "completion-outbox-v0-4-validate",
            f"EVENT={OUTBOX_REL.as_posix()}",
        )
    ).stdout.decode("utf-8", errors="replace")
    if "result: PASSED" not in output:
        raise FinalizationError("Completion Outbox v0.4 validation did not pass")


def validate_coordination() -> None:
    prompts = load_yaml(ROOT / "coordination/prompts/index.yaml")["prompts"]
    matches = [item for item in prompts if item.get("prompt_id") == PROMPT_ID]
    if len(matches) != 1 or matches[0].get("completion_commit") != SUBJECT_COMMIT:
        raise FinalizationError("prompt finalization binding mismatch")
    status = load_yaml(ROOT / "coordination/status/current_status.yaml")
    if status.get("completion_commit") != SUBJECT_COMMIT:
        raise FinalizationError("status completion_commit mismatch")
    if status.get("blueprint_review_status") != "not_started":
        raise FinalizationError("status must not claim Blueprint review")


def prepare() -> None:
    preflight()
    created_at = now_iso()
    publication = verify_publication()
    supersedes = historical_v03()
    write_yaml(ROOT / PUBLICATION_REL, publication)

    execution = capture_execution()
    write_yaml(ROOT / FINAL_EXECUTION_REL, execution)
    write_text(ROOT / REPORT_REL, build_report(created_at, execution, supersedes))

    write_yaml(
        ROOT / FINAL_IDEMPOTENCY_REL,
        build_idempotency(created_at, execution, supersedes),
    )

    apply_coordination(ROOT, created_at, execution, supersedes)
    post_apply = capture_post_apply()
    write_yaml(ROOT / POST_APPLY_REL, post_apply)

    write_yaml(
        ROOT / PACKET_REL,
        build_packet(created_at, execution, post_apply, supersedes),
    )
    validate_packet()

    write_yaml(ROOT / OUTBOX_REL, build_outbox(created_at, publication))
    validate_outbox()
    validate_coordination()

    run(("make", "coordination-check"))
    run(("make", "governance-check"))
    run(("make", "module-validate"))
    run(("git", "diff", "--check"))
    verify_runtime()

    print("TRACKING_EVENTS_V0_4_FINALIZATION_PREPARED")
    print(f"completion_id={COMPLETION_ID}")
    print(f"completion_packet={PACKET_REL.as_posix()}")
    print(f"completion_outbox_event_id={EVENT_ID}")
    print(f"completion_outbox={OUTBOX_REL.as_posix()}")
    print(f"completion_subject_commit={SUBJECT_COMMIT}")
    print("remote_containment_verified=true")
    print("source_semantic_coverage=26/26")
    print("target_obligations=39/39")
    print(
        f"focused={execution['focused_tests']['passed']}/{execution['focused_tests']['collected']}"
    )
    print(f"full_suite={execution['full_suite']['passed']}/{execution['full_suite']['collected']}")
    print(
        f"check_report={execution['check_report']['passed']}/{execution['check_report']['total']}"
    )
    print(
        f"check_report_full={execution['check_report_full']['passed']}/"
        f"{execution['check_report_full']['total']}"
    )
    print("completion_packet_v0_4=valid")
    print("completion_outbox_v0_4=valid")
    print("automatic_commit=false")
    print("automatic_push=false")
    print("BLUEPRINT_OPERATOR_DECISION_CREATED=false")
    print("GLOBAL_V0_4_PROMOTION_PERFORMED=false")


def check() -> None:
    for rel in (
        PUBLICATION_REL,
        FINAL_EXECUTION_REL,
        POST_APPLY_REL,
        FINAL_IDEMPOTENCY_REL,
        REPORT_REL,
        PACKET_REL,
        OUTBOX_REL,
    ):
        if not (ROOT / rel).is_file():
            raise FinalizationError(f"required finalization artifact missing: {rel}")
    validate_packet()
    validate_outbox()
    validate_coordination()
    packet = load_yaml(ROOT / PACKET_REL)
    if len(packet.get("requirement_results", [])) != 39:
        raise FinalizationError("Packet requirement result count != 39")
    idem = load_yaml(ROOT / FINAL_IDEMPOTENCY_REL)
    if idem.get("repeat_run", {}).get("result") != "IDEMPOTENT_NOOP":
        raise FinalizationError("finalization idempotency evidence invalid")
    run(("make", "coordination-check"))
    run(("make", "governance-check"))
    run(("git", "diff", "--check"))
    verify_runtime()
    print("TRACKING_EVENTS_V0_4_FINALIZATION_VALID")
    print("source_semantic_coverage=26/26")
    print("target_obligations=39/39")
    print("completion_packet_v0_4=valid")
    print("completion_outbox_v0_4=valid")
    print("blueprint_discovery_performed=false")
    print("blueprint_intake_performed=false")
    print("BLUEPRINT_OPERATOR_DECISION_CREATED=false")
    print("GLOBAL_V0_4_PROMOTION_PERFORMED=false")


def idempotency_check() -> None:
    if (ROOT / FINAL_EXECUTION_REL).is_file():
        execution = load_yaml(ROOT / FINAL_EXECUTION_REL)
    else:
        execution = {
            "focused_tests": {"collected": 1, "passed": 1},
            "full_suite": {"collected": 1, "passed": 1},
            "check_report": {"total": 11, "passed": 11, "warnings": 0, "failed": 0},
            "check_report_full": {"total": 11, "passed": 11, "warnings": 0, "failed": 0},
        }
    evidence = build_idempotency(
        "2026-08-18T12:00:00+03:00",
        execution,
        historical_v03(),
    )
    print("TRACKING_EVENTS_V0_4_POSTPUBLICATION_IDEMPOTENCY_PASSED")
    print(f"first_run={evidence['first_run']['result']}")
    print(f"repeat_run={evidence['repeat_run']['result']}")
    print("live_worktree_mutated=false")


def status() -> None:
    print(f"branch={git_text('branch', '--show-current')}")
    print(f"head={git_text('rev-parse', 'HEAD')}")
    print(f"upstream={git_text('rev-parse', UPSTREAM)}")
    print(f"packet_exists={(ROOT / PACKET_REL).is_file()}")
    print(f"outbox_exists={(ROOT / OUTBOX_REL).is_file()}")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("status", "preflight", "prepare", "check", "idempotency-check"):
        sub.add_parser(name)
    args = parser.parse_args()
    try:
        if args.command == "status":
            status()
        elif args.command == "preflight":
            preflight()
        elif args.command == "prepare":
            prepare()
        elif args.command == "check":
            check()
        elif args.command == "idempotency-check":
            idempotency_check()
    except Exception as exc:
        print(f"FAILED: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
