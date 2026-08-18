from __future__ import annotations

import argparse
import hashlib
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
BLUEPRINT_COMMIT = "3940c70f4fbe56aa8f8c834d8cbee56eeb8b5c11"

BRANCH = "feature/logistics-tracking-events-contract-v01"
BASE_HEAD = "ecf3e23223cec90e47ac206be9a33c3e3b02673c"
IMPLEMENTATION_COMMIT = "bbc298e294bd9e7e6cca976d4a8077c52c4a51ff"

PROMPT_ID = "logistics_service_tracking_events_v0_1"
CONTRACT_REL = Path(
    "coordination/prompt_contracts/logistics_service/"
    "logistics_service_tracking_events_v0_1/"
    "logistics_service_tracking_events_v0_1__contract_v0_4_reference_v0_2.yaml"
)
CONTRACT_SHA = "73f0fe602398536c940f3a6295a3b7d3263f302fba65b68e21d5c90355250981"
CONTRACT_PAYLOAD_SHA = "02775affa37cd6b21c8251dd05f379cb727bfecd9bebe6f948d2ac8b987c2138"
SOURCE_PROMPT_SHA = "8158ff1feb9c2416aac97f70ce20110de3195d5239a343be940705d096242094"

SOURCE_SNAPSHOT_BP = (
    "coordination/prompt_contracts/logistics_service/"
    "logistics_service_tracking_events_v0_1/source_prompt_snapshot.md"
)
SEMANTIC_DECISION_BP = (
    "coordination/internal_work/blueprint/governance/"
    "2026-08-17__blueprint__tracking_events_v0_4_"
    "semantic_fidelity_operator_decision_v0_1.yaml"
)

EVIDENCE_DIR = Path("coordination/evidence/tracking_events_v0_4")
AUDIT_REL = EVIDENCE_DIR / "source_obligation_audit.yaml"
TELEGRAM_REL = EVIDENCE_DIR / "telegram_handoff.yaml"
TEST_CATALOG_REL = EVIDENCE_DIR / "required_test_catalog.yaml"
EXECUTION_REL = EVIDENCE_DIR / "validation_execution.yaml"
READING_REL = EVIDENCE_DIR / "required_reading.yaml"
IDEMPOTENCY_REL = EVIDENCE_DIR / "completion_finalization_idempotency.yaml"
SUBJECT_REL = EVIDENCE_DIR / "completion_subject_prepublication.yaml"
REPORT_REL = Path(
    "coordination/reports/completion/"
    "logistics_service_tracking_events_v0_1_completion_subject_v0_4.md"
)

RUNTIME_PATHS = (
    "app/domain/events.py",
    "app/domain/tracking.py",
    "app/services/tracking_contract_service.py",
    "examples/fixtures/tracking_events/synthetic_tracking_events.yaml",
)

COORDINATION_STATE_PATHS = (
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
)

REQUIRED_COMMANDS = (
    ("SUBJECT-CHECK-001", ("make", "tracking-events-check")),
    ("SUBJECT-CHECK-002", ("make", "governance-check")),
    ("SUBJECT-CHECK-003", ("make", "coordination-check")),
    ("SUBJECT-CHECK-004", ("make", "check")),
    ("SUBJECT-CHECK-005", ("make", "check-report")),
    ("SUBJECT-CHECK-006", ("make", "check-report-full")),
    ("SUBJECT-CHECK-007", ("make", "module-validate")),
    ("SUBJECT-CHECK-008", ("git", "diff", "--check")),
    ("SUBJECT-CHECK-009", ("git", "status", "--short")),
    ("SUBJECT-CHECK-010", ("make", "tracking-events-preview")),
    ("SUBJECT-CHECK-011", ("make", "tracking-events-v0-4-evidence-check")),
)

SYNTHETIC_COMPLETION_COMMIT = "a" * 40
HEX40 = re.compile(r"^[0-9a-f]{40}$")


class SubjectError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now(ZoneInfo("Europe/Kyiv")).isoformat(timespec="seconds")


def run(
    command: tuple[str, ...],
    *,
    cwd: Path = ROOT,
    allowed: tuple[int, ...] = (0,),
) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        list(command),
        cwd=cwd,
        check=False,
        capture_output=True,
    )
    if result.returncode not in allowed:
        text = (result.stdout + result.stderr).decode("utf-8", errors="replace")
        raise SubjectError(
            f"command failed ({result.returncode}): {' '.join(command)}\n" + text[-8000:]
        )
    return result


def git_text(*args: str) -> str:
    return run(("git", *args)).stdout.decode("utf-8", errors="replace").strip()


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SubjectError(f"YAML root must be a mapping: {path}")
    return data


def write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        width=100,
    )
    path.write_text(text, encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def blueprint_blob(rel: str) -> bytes:
    return run(("git", "-C", str(BLUEPRINT), "show", f"{BLUEPRINT_COMMIT}:{rel}")).stdout


def contract() -> dict[str, Any]:
    path = ROOT / CONTRACT_REL
    if not path.is_file():
        raise SubjectError(f"Prompt Contract missing: {CONTRACT_REL}")
    if sha_file(path) != CONTRACT_SHA:
        raise SubjectError("Prompt Contract file SHA mismatch")
    data = load_yaml(path)
    if data.get("integrity", {}).get("payload_sha256") != CONTRACT_PAYLOAD_SHA:
        raise SubjectError("Prompt Contract payload SHA mismatch")
    if data.get("source_prompt", {}).get("sha256") != SOURCE_PROMPT_SHA:
        raise SubjectError("Prompt Contract source prompt SHA mismatch")
    return data


def verify_blueprint_anchor() -> dict[str, Any]:
    contract_raw = blueprint_blob(CONTRACT_REL.as_posix())
    if sha_bytes(contract_raw) != CONTRACT_SHA:
        raise SubjectError("Blueprint Prompt Contract SHA mismatch")

    source_raw = blueprint_blob(SOURCE_SNAPSHOT_BP)
    if sha_bytes(source_raw) != SOURCE_PROMPT_SHA:
        raise SubjectError("Blueprint source snapshot SHA mismatch")

    decision_raw = blueprint_blob(SEMANTIC_DECISION_BP)
    decision = yaml.safe_load(decision_raw.decode("utf-8"))
    if not isinstance(decision, dict):
        raise SubjectError("semantic decision must be a mapping")

    decision_map = decision.get("decision", {})
    effects = decision.get("effects", {})
    if decision_map.get("value") != "ACCEPT_SEMANTIC_FIDELITY":
        raise SubjectError("semantic fidelity decision mismatch")
    if decision_map.get("semantic_coverage") != "26/26":
        raise SubjectError("semantic fidelity coverage mismatch")
    if effects.get("tracking_events_completion_accepted") is not False:
        raise SubjectError("semantic decision must not accept completion")
    if effects.get("global_v0_4_promotion_performed") is not False:
        raise SubjectError("semantic decision must not promote v0.4")

    return {
        "blueprint_commit": BLUEPRINT_COMMIT,
        "contract_sha256": CONTRACT_SHA,
        "source_prompt_sha256": SOURCE_PROMPT_SHA,
        "semantic_fidelity": "ACCEPT_SEMANTIC_FIDELITY",
        "semantic_coverage": "26/26",
        "tracking_events_completion_accepted": False,
        "global_v0_4_promotion_performed": False,
    }


def verify_runtime() -> None:
    drift = git_text(
        "diff",
        "--name-only",
        IMPLEMENTATION_COMMIT,
        "--",
        *RUNTIME_PATHS,
    )
    if drift:
        raise SubjectError(f"Tracking runtime drift detected: {drift}")


def verify_live_coordination_is_still_historical_v02() -> None:
    prompts = load_yaml(ROOT / "coordination/prompts/index.yaml")
    rows = prompts.get("prompts")
    if not isinstance(rows, list):
        raise SubjectError("prompt index invalid")

    matches = [row for row in rows if isinstance(row, dict) and row.get("prompt_id") == PROMPT_ID]
    if len(matches) != 1:
        raise SubjectError("Tracking prompt record must be unique")

    row = matches[0]
    if row.get("status") != "completed_in_module":
        raise SubjectError("historical Tracking prompt status changed")
    if row.get("completion_schema_version") != "module_completion_packet_v0_2":
        raise SubjectError("premature v0.4 prompt-state mutation detected")
    if row.get("completion_commit_status") != "derive_after_git_commit":
        raise SubjectError("historical v0.2 completion deferral changed")
    if row.get("completion_commit") is not None:
        raise SubjectError("unexpected completion_commit before subject publication")

    status = load_yaml(ROOT / "coordination/status/current_status.yaml")
    protocol = status.get("completion_protocol", {})
    if protocol.get("schema_version") != "module_completion_packet_v0_2":
        raise SubjectError("premature v0.4 current_status mutation detected")


def preflight() -> None:
    if git_text("branch", "--show-current") != BRANCH:
        raise SubjectError("branch mismatch")
    if git_text("rev-parse", "HEAD") != BASE_HEAD:
        raise SubjectError("HEAD mismatch")
    divergence = git_text(
        "rev-list",
        "--left-right",
        "--count",
        "HEAD...@{upstream}",
    )
    if divergence != "0\t0":
        raise SubjectError(f"upstream divergence must be 0 0: {divergence}")
    if git_text("diff", "--cached", "--name-only"):
        raise SubjectError("real Git index must be clean")

    data = contract()
    target_total = sum(
        len(data[key])
        for key in (
            "implementation_obligations",
            "verification_obligations",
            "completion_evidence_obligations",
        )
    )
    if target_total != 39:
        raise SubjectError(f"target obligation total must be 39: {target_total}")

    verify_blueprint_anchor()
    verify_runtime()
    verify_live_coordination_is_still_historical_v02()

    audit = load_yaml(ROOT / AUDIT_REL)
    rows = audit.get("source_obligations")
    if not isinstance(rows, list) or len(rows) != 26:
        raise SubjectError("source obligation audit must contain 26 rows")

    run(("make", "tracking-events-v0-4-evidence-check"))

    print("TRACKING_EVENTS_V0_4_SUBJECT_PREFLIGHT_PASSED")
    print("source_semantic_coverage=26/26")
    print("target_obligations_total=39")
    print("ce_009_publication_evidence=pending")
    print("packet_creation_allowed_now=false")
    print("live_coordination_v0_4_mutation=false")
    print("BLUEPRINT_OPERATOR_DECISION_CREATED=false")
    print("GLOBAL_V0_4_PROMOTION_PERFORMED=false")


def parse_collected(text: str) -> int:
    matches = re.findall(r"(\d+) tests? collected", text)
    if not matches:
        raise SubjectError("pytest collection total not found")
    return int(matches[-1])


def parse_passed(text: str) -> int:
    matches = re.findall(r"(\d+) passed", text)
    if not matches:
        raise SubjectError("pytest pass total not found")
    return int(matches[-1])


def parse_check_totals(text: str) -> dict[str, int]:
    match = re.search(
        r"Checks:\s*(\d+)\s+total\s*\|\s*(\d+)\s+passed\s*\|\s*"
        r"(\d+)\s+warning\s*\|\s*(\d+)\s+failed",
        text,
    )
    if match is None:
        raise SubjectError("check-report totals not found")
    total, passed, warnings, failed = map(int, match.groups())
    return {
        "total": total,
        "passed": passed,
        "warnings": warnings,
        "failed": failed,
    }


def execute_record(
    check_id: str,
    command: tuple[str, ...],
) -> tuple[dict[str, Any], str]:
    executed_at = now_iso()
    result = run(command)
    raw = result.stdout + result.stderr
    return (
        {
            "check_id": check_id,
            "command": " ".join(command),
            "result": "passed",
            "exit_code": result.returncode,
            "executed_at": executed_at,
            "output_sha256": sha_bytes(raw),
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
    focused_run = (
        python,
        "-m",
        "pytest",
        "-q",
        "-o",
        "addopts=",
        *FOCUSED_TESTS,
    )
    full_collect = (
        python,
        "-m",
        "pytest",
        "--collect-only",
        "-q",
        "-o",
        "addopts=",
    )
    full_run = (
        python,
        "-m",
        "pytest",
        "-q",
        "-o",
        "addopts=",
    )

    fc, fc_text = execute_record("SUBJECT-TEST-FOCUSED-COLLECT", focused_collect)
    fr, fr_text = execute_record("SUBJECT-TEST-FOCUSED-RUN", focused_run)
    ac, ac_text = execute_record("SUBJECT-TEST-FULL-COLLECT", full_collect)
    ar, ar_text = execute_record("SUBJECT-TEST-FULL-RUN", full_run)

    focused_collected = parse_collected(fc_text)
    focused_passed = parse_passed(fr_text)
    full_collected = parse_collected(ac_text)
    full_passed = parse_passed(ar_text)

    if focused_collected != focused_passed:
        raise SubjectError(
            f"focused collected/passed mismatch: {focused_collected}/{focused_passed}"
        )
    if full_collected != full_passed:
        raise SubjectError(f"full collected/passed mismatch: {full_collected}/{full_passed}")

    required = []
    check_report = None
    check_report_full = None
    for check_id, command in REQUIRED_COMMANDS:
        record, output = execute_record(check_id, command)
        required.append(record)
        if check_id == "SUBJECT-CHECK-005":
            check_report = parse_check_totals(output)
        elif check_id == "SUBJECT-CHECK-006":
            check_report_full = parse_check_totals(output)

    if check_report is None or check_report_full is None:
        raise SubjectError("check-report totals missing")
    if check_report["failed"] or check_report_full["failed"]:
        raise SubjectError("check-report contains failed checks")

    return {
        "schema_version": ("logistics_tracking_events_v0_4_subject_validation_execution_v0_1"),
        "captured_at": now_iso(),
        "focused_tests": {
            "paths": list(FOCUSED_TESTS),
            "collected": focused_collected,
            "passed": focused_passed,
        },
        "full_suite": {
            "collected": full_collected,
            "passed": full_passed,
        },
        "check_report": check_report,
        "check_report_full": check_report_full,
        "test_commands": [fc, fr, ac, ar],
        "required_commands": required,
        "generated_artifact_handling": {
            "check_report_read_only": True,
            "check_report_full_read_only": True,
            "tracking_events_preview_read_only": True,
            "generated_diagnostics_committed": False,
        },
    }


def build_required_reading() -> dict[str, Any]:
    blueprint = verify_blueprint_anchor()
    paths = (
        "docs/architecture/adapters/provider_adapter_policy.md",
        "docs/architecture/provider_adapter_contract.md",
        "docs/operations/provider_adapter_contract_runbook.md",
        "docs/operations/provider_adapter_contract_recovery.md",
        "docs/architecture/tracking_event_contract.md",
        "docs/architecture/boundaries/notification_handoff_boundary.md",
        "docs/operations/tracking_events_runbook.md",
        "docs/operations/tracking_events_recovery.md",
    )
    artifacts = []
    for rel in paths:
        path = ROOT / rel
        if not path.is_file():
            raise SubjectError(f"required Logistics artifact missing: {rel}")
        artifacts.append({"path": rel, "sha256": sha_file(path)})

    return {
        "schema_version": ("logistics_tracking_events_v0_4_required_reading_v0_1"),
        "blueprint": blueprint,
        "module_authoritative_artifacts": artifacts,
        "approved_blueprint_navigation_used": True,
        "authoritative_paths_reused": True,
        "duplicate_domain_hierarchy_created": False,
    }


def seed_coordination(root: Path) -> None:
    for rel in COORDINATION_STATE_PATHS:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(run(("git", "show", f"{BASE_HEAD}:{rel}")).stdout)


def apply_finalized_coordination(
    root: Path,
    completion_commit: str,
    created_at: str,
) -> list[str]:
    if not HEX40.fullmatch(completion_commit):
        raise SubjectError("completion_commit must be full lowercase 40-hex")

    changed = []

    prompt_path = root / "coordination/prompts/index.yaml"
    prompt_data = load_yaml(prompt_path)
    prompts = prompt_data["prompts"]
    matches = [row for row in prompts if row.get("prompt_id") == PROMPT_ID]
    if len(matches) != 1:
        raise SubjectError("Tracking prompt record must be unique")
    row = matches[0]
    row.update(
        {
            "status": "completed_in_module",
            "module_execution_status": "completed_by_module",
            "blueprint_review_status": "not_started",
            "completion_report": (
                "coordination/reports/completion/"
                "logistics_service_tracking_events_v0_1_"
                "completion_report_v0_4_reference.md"
            ),
            "completion_commit": completion_commit,
            "completion_commit_status": "recorded",
            "completion_schema_version": "module_completion_packet_v0_4",
            "completion_protocol_version": ("module_completion_packet_protocol_v0_4"),
            "completion_id": ("logistics_service_tracking_events_v0_1_completed_v0_4_reference"),
        }
    )
    prompt_data["active_prompt_id"] = None
    before = prompt_path.read_text(encoding="utf-8")
    after = yaml.safe_dump(
        prompt_data,
        sort_keys=False,
        allow_unicode=True,
        width=100,
    )
    if before != after:
        prompt_path.write_text(after, encoding="utf-8")
        changed.append(prompt_path.relative_to(root).as_posix())

    status_path = root / "coordination/status/current_status.yaml"
    status = load_yaml(status_path)
    status.update(
        {
            "status": "completed_in_module",
            "source_prompt_id": PROMPT_ID,
            "completion_commit": completion_commit,
            "completion_commit_status": "recorded",
            "blueprint_review_status": "not_started",
            "push_status": "pushed",
            "updated_at": created_at,
        }
    )
    status["completion_protocol"] = {
        "schema_version": "module_completion_packet_v0_4",
        "protocol_version": "module_completion_packet_protocol_v0_4",
        "completion_id": ("logistics_service_tracking_events_v0_1_completed_v0_4_reference"),
    }
    before = status_path.read_text(encoding="utf-8")
    after = yaml.safe_dump(
        status,
        sort_keys=False,
        allow_unicode=True,
        width=100,
    )
    if before != after:
        status_path.write_text(after, encoding="utf-8")
        changed.append(status_path.relative_to(root).as_posix())

    return changed


def build_idempotency(created_at: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="logistics-v04-finalization-idempotency-") as tmp:
        root = Path(tmp)
        seed_coordination(root)

        first = apply_finalized_coordination(
            root,
            SYNTHETIC_COMPLETION_COMMIT,
            created_at,
        )
        first_snapshot = {
            rel: (root / rel).read_bytes()
            for rel in (
                "coordination/prompts/index.yaml",
                "coordination/status/current_status.yaml",
            )
        }

        second = apply_finalized_coordination(
            root,
            SYNTHETIC_COMPLETION_COMMIT,
            created_at,
        )
        second_snapshot = {
            rel: (root / rel).read_bytes()
            for rel in (
                "coordination/prompts/index.yaml",
                "coordination/status/current_status.yaml",
            )
        }

    if not first:
        raise SubjectError("first isolated finalization was a no-op")
    if second:
        raise SubjectError(f"repeat isolated finalization changed state: {second}")
    if first_snapshot != second_snapshot:
        raise SubjectError("repeat isolated finalization state differs")

    return {
        "schema_version": (
            "logistics_tracking_events_v0_4_completion_finalization_idempotency_v0_1"
        ),
        "isolated_sandbox": True,
        "synthetic_completion_commit": SYNTHETIC_COMPLETION_COMMIT,
        "first_run": {
            "result": "APPLIED",
            "changed_paths": first,
        },
        "repeat_run": {
            "result": "IDEMPOTENT_NOOP",
            "changed_paths": second,
        },
        "semantic_state_equal_after_repeat": True,
        "live_worktree_mutated": False,
        "packet_created": False,
        "outbox_created": False,
    }


def build_subject_manifest(
    created_at: str,
    execution: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": ("logistics_tracking_events_v0_4_completion_subject_prepublication_v0_1"),
        "created_at": created_at,
        "branch": BRANCH,
        "base_head": BASE_HEAD,
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "prompt_id": PROMPT_ID,
        "source_semantic_coverage": "26/26",
        "prompt_contract_target_obligations_total": 39,
        "prepublication_target_obligations_satisfied": 38,
        "pending_completion_evidence_obligation": "CE-009",
        "pending_reason": (
            "Completion commit, push and upstream-divergence evidence can only "
            "be recorded after this completion subject is committed and pushed."
        ),
        "completion_packet_created": False,
        "completion_outbox_created": False,
        "live_v0_4_terminal_coordination_applied": False,
        "historical_v0_2_terminal_coordination_preserved": True,
        "focused_tests": execution["focused_tests"],
        "full_suite": execution["full_suite"],
        "check_report": execution["check_report"],
        "check_report_full": execution["check_report_full"],
        "next_gate": (
            "Commit and push this completion subject, verify remote containment, "
            "then finalize v0.4 coordination and build Packet/Outbox."
        ),
        "safety": {
            "preview_only": True,
            "live_write": False,
            "provider_call_performed": False,
            "Telegram_API_call": False,
            "cross_repository_write": False,
            "credentials_added": False,
        },
    }


def build_report(
    created_at: str,
    execution: dict[str, Any],
) -> str:
    focused = execution["focused_tests"]
    full = execution["full_suite"]
    check_report = execution["check_report"]
    check_report_full = execution["check_report_full"]

    return f"""# Tracking Events v0.4 completion subject

## RESULT

`LOGISTICS_TRACKING_EVENTS_V0_4_COMPLETION_SUBJECT_READY_FOR_GIT_PUBLICATION`

The Tracking Events runtime is unchanged. The v0.4 command/evidence migration
is prepared for the first publication commit.

## Coverage

- Source semantic coverage: `26/26`
- Prompt Contract target obligations total: `39`
- Prepublication target obligations satisfied: `38/39`
- Pending obligation: `CE-009`

CE-009 requires the real completion commit plus push and upstream-divergence
evidence. Those facts do not exist until this completion subject is committed
and pushed.

## Validation

- Focused collected: `{focused["collected"]}`
- Focused passed: `{focused["passed"]}`
- Full-suite collected: `{full["collected"]}`
- Full-suite passed: `{full["passed"]}`
- check-report: `{check_report["passed"]}/{check_report["total"]}`
- check-report-full: `{check_report_full["passed"]}/{check_report_full["total"]}`

Detailed execution evidence: `{EXECUTION_REL.as_posix()}`

## Publication boundary

- Completion Packet v0.4 created: `false`
- Completion Outbox v0.4 created: `false`
- Live v0.4 terminal coordination applied: `false`
- Historical v0.2 terminal coordination preserved: `true`
- Automatic commit: `false`
- Automatic push: `false`

After this subject is committed and pushed, the next phase records the real
completion commit and remote containment, then creates the immutable Packet
v0.4 and Completion Outbox v0.4.

BLUEPRINT_OPERATOR_DECISION_CREATED=false

GLOBAL_V0_4_PROMOTION_PERFORMED=false
"""


def prepare() -> None:
    preflight()

    if (ROOT / SUBJECT_REL).is_file():
        subject_check()
        print("TRACKING_EVENTS_V0_4_SUBJECT_PREPARE_IDEMPOTENT_NOOP")
        return

    created_at = now_iso()

    execution = capture_execution()
    write_yaml(ROOT / EXECUTION_REL, execution)

    reading = build_required_reading()
    write_yaml(ROOT / READING_REL, reading)

    idempotency = build_idempotency(created_at)
    write_yaml(ROOT / IDEMPOTENCY_REL, idempotency)

    subject = build_subject_manifest(created_at, execution)
    write_yaml(ROOT / SUBJECT_REL, subject)

    write_text(ROOT / REPORT_REL, build_report(created_at, execution))

    run(("make", "governance-check"))
    run(("make", "coordination-check"))
    run(("make", "module-validate"))
    run(("git", "diff", "--check"))

    verify_live_coordination_is_still_historical_v02()
    verify_runtime()

    print("TRACKING_EVENTS_V0_4_COMPLETION_SUBJECT_PREPARED")
    print(f"subject_manifest={SUBJECT_REL.as_posix()}")
    print(f"subject_report={REPORT_REL.as_posix()}")
    print(
        f"focused={execution['focused_tests']['passed']}/{execution['focused_tests']['collected']}"
    )
    print(f"full_suite={execution['full_suite']['passed']}/{execution['full_suite']['collected']}")
    print("prepublication_target_obligations=38/39")
    print("pending_obligation=CE-009")
    print("completion_packet_created=false")
    print("completion_outbox_created=false")
    print("automatic_commit=false")
    print("automatic_push=false")


def subject_check() -> None:
    preflight()

    for rel in (
        EXECUTION_REL,
        READING_REL,
        IDEMPOTENCY_REL,
        SUBJECT_REL,
        REPORT_REL,
    ):
        if not (ROOT / rel).is_file():
            raise SubjectError(f"required subject artifact missing: {rel}")

    execution = load_yaml(ROOT / EXECUTION_REL)
    subject = load_yaml(ROOT / SUBJECT_REL)
    idempotency = load_yaml(ROOT / IDEMPOTENCY_REL)

    if subject.get("prepublication_target_obligations_satisfied") != 38:
        raise SubjectError("subject must record 38/39 prepublication obligations")
    if subject.get("pending_completion_evidence_obligation") != "CE-009":
        raise SubjectError("subject must identify CE-009 as publication-pending")
    if subject.get("completion_packet_created") is not False:
        raise SubjectError("subject must not claim Packet creation")
    if idempotency.get("repeat_run", {}).get("result") != "IDEMPOTENT_NOOP":
        raise SubjectError("finalization idempotency evidence invalid")
    if execution.get("check_report", {}).get("failed") != 0:
        raise SubjectError("check-report evidence contains failure")
    if execution.get("check_report_full", {}).get("failed") != 0:
        raise SubjectError("check-report-full evidence contains failure")

    run(("make", "governance-check"))
    run(("make", "coordination-check"))
    run(("git", "diff", "--check"))
    verify_live_coordination_is_still_historical_v02()
    verify_runtime()

    print("TRACKING_EVENTS_V0_4_COMPLETION_SUBJECT_VALID")
    print("source_semantic_coverage=26/26")
    print("prepublication_target_obligations=38/39")
    print("pending_obligation=CE-009")
    print("completion_packet_created=false")
    print("completion_outbox_created=false")
    print("live_v0_4_terminal_coordination_applied=false")


def idempotency_check() -> None:
    evidence = build_idempotency("2026-08-18T12:00:00+03:00")
    if evidence["repeat_run"]["result"] != "IDEMPOTENT_NOOP":
        raise SubjectError("finalization idempotency failed")
    print("TRACKING_EVENTS_V0_4_FINALIZATION_IDEMPOTENCY_PASSED")
    print("first_run=APPLIED")
    print("repeat_run=IDEMPOTENT_NOOP")
    print("live_worktree_mutated=false")


def status() -> None:
    print(f"branch={git_text('branch', '--show-current')}")
    print(f"head={git_text('rev-parse', 'HEAD')}")
    print(
        "upstream_divergence="
        + git_text(
            "rev-list",
            "--left-right",
            "--count",
            "HEAD...@{upstream}",
        )
    )
    print(f"subject_exists={(ROOT / SUBJECT_REL).is_file()}")
    print("completion_packet_created=false")
    print("completion_outbox_created=false")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("preflight")
    sub.add_parser("prepare")
    sub.add_parser("check")
    sub.add_parser("idempotency-check")
    args = parser.parse_args()

    try:
        if args.command == "status":
            status()
        elif args.command == "preflight":
            preflight()
        elif args.command == "prepare":
            prepare()
        elif args.command == "check":
            subject_check()
        elif args.command == "idempotency-check":
            idempotency_check()
    except Exception as exc:
        print(f"FAILED: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
