from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml

EXPECTED_SCHEMA = "module_completion_packet_v0_4"
EXPECTED_PROTOCOL = "module_completion_packet_protocol_v0_4"
EXPECTED_STATUS = "completed_in_module_pending_blueprint_review"
EXPECTED_CONTRACT_SCHEMA = "module_prompt_contract_v0_4"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$")
OK = {"ok", "passed", "pass", "green", True}
REQUIRED_CHECKS = ("check_report", "tests", "governance_check")
TARGET_CATEGORIES = {
    "implementation_obligations": "implementation",
    "verification_obligations": "verification",
    "completion_evidence_obligations": "completion_evidence",
}
FORBIDDEN_DECISION_FIELDS = {
    "operator_decision",
    "accepted_by_blueprint",
    "blueprint_review",
    "automatic_acceptance",
    "automatic_return",
}


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return data


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


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_under(root: Path, rel: str, label: str) -> Path:
    candidate = (root / rel).resolve()
    root_resolved = root.resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(f"{label} escapes repository root: {rel}") from exc
    return candidate


def non_empty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def require_hash(value: Any, label: str, errors: list[str]) -> None:
    if not isinstance(value, str) or HEX64.fullmatch(value) is None:
        errors.append(f"{label} must be a 64-character lowercase sha256")


def validate_packet(
    root: Path,
    packet_path: Path,
    data: dict[str, Any] | None = None,
    *,
    template_mode: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    packet_path = packet_path.resolve()
    packet = copy.deepcopy(data) if data is not None else load_yaml(packet_path)
    errors: list[str] = []
    warnings: list[str] = []

    if packet.get("schema_version") != EXPECTED_SCHEMA:
        errors.append("schema_version mismatch")
    if packet.get("protocol_version") != EXPECTED_PROTOCOL:
        errors.append("protocol_version mismatch")
    if packet.get("status") != EXPECTED_STATUS:
        errors.append("status must remain completed_in_module_pending_blueprint_review")
    if packet.get("immutable") is not True:
        errors.append("immutable must be true")

    for key in (
        "completion_id",
        "module_id",
        "prompt_id",
        "phase",
        "created_at",
        "report_id",
        "report_path",
        "report_sha256",
        "implementation_base_commit",
        "implementation_commit",
        "branch",
    ):
        if not non_empty(packet.get(key)):
            errors.append(f"{key} missing")

    completion_id = packet.get("completion_id")
    if not template_mode and isinstance(completion_id, str):
        if SAFE_ID.fullmatch(completion_id) is None:
            errors.append("completion_id contains unsafe characters")
        expected_path = (
            root / "coordination/completion_packets/records" / f"{completion_id}.yaml"
        ).resolve()
        if packet_path != expected_path:
            errors.append("immutable completion packet instance path mismatch")

    if not template_mode:
        for key in ("implementation_base_commit", "implementation_commit"):
            value = packet.get(key)
            if not isinstance(value, str) or HEX40.fullmatch(value) is None:
                errors.append(f"{key} must be a full 40-character lowercase Git hash")
        require_hash(packet.get("report_sha256"), "report_sha256", errors)

    for forbidden in FORBIDDEN_DECISION_FIELDS:
        if forbidden in packet:
            errors.append(
                "module completion packet must not contain Blueprint decision field: " + forbidden
            )

    prompt_contract = packet.get("prompt_contract")
    if not isinstance(prompt_contract, dict):
        errors.append("prompt_contract must be a mapping")
        prompt_contract = {}
    if prompt_contract.get("schema_version") != EXPECTED_CONTRACT_SCHEMA:
        errors.append("prompt_contract.schema_version mismatch")
    for key in (
        "contract_id",
        "path",
        "file_sha256",
        "payload_sha256",
        "source_prompt_sha256",
    ):
        if not non_empty(prompt_contract.get(key)):
            errors.append(f"prompt_contract.{key} missing")
    if not template_mode:
        for key in ("file_sha256", "payload_sha256", "source_prompt_sha256"):
            require_hash(prompt_contract.get(key), f"prompt_contract.{key}", errors)

    expected_obligations: dict[str, str] = {}
    contract: dict[str, Any] | None = None
    if not template_mode and non_empty(prompt_contract.get("path")):
        try:
            contract_path = safe_under(
                root,
                prompt_contract["path"],
                "prompt_contract.path",
            )
        except ValueError as exc:
            errors.append(str(exc))
        else:
            if not contract_path.is_file():
                errors.append("prompt_contract.path does not exist")
            else:
                try:
                    contract = load_yaml(contract_path)
                except Exception as exc:
                    errors.append(f"prompt contract YAML invalid: {exc}")
                else:
                    if contract.get("schema_version") != EXPECTED_CONTRACT_SCHEMA:
                        errors.append("bound prompt contract schema mismatch")
                    metadata = contract.get("metadata")
                    if not isinstance(metadata, dict):
                        errors.append("bound prompt contract metadata missing")
                        metadata = {}
                    if metadata.get("contract_id") != prompt_contract.get("contract_id"):
                        errors.append("prompt contract id mismatch")
                    if metadata.get("module_id") != packet.get("module_id"):
                        errors.append("prompt contract module_id mismatch")
                    if metadata.get("prompt_id") != packet.get("prompt_id"):
                        errors.append("prompt contract prompt_id mismatch")
                    if metadata.get("status") != "candidate_reference_only":
                        errors.append(
                            "bound Prompt Contract v0.4 must remain candidate_reference_only"
                        )
                    promotion = contract.get("promotion")
                    if (
                        not isinstance(promotion, dict)
                        or promotion.get("promotion_performed") is not False
                    ):
                        errors.append("bound Prompt Contract v0.4 promotion state invalid")
                    if sha256_file(contract_path) != prompt_contract.get("file_sha256"):
                        errors.append("prompt contract file SHA-256 mismatch")
                    integrity = contract.get("integrity")
                    if not isinstance(integrity, dict):
                        errors.append("bound prompt contract integrity missing")
                    elif integrity.get("payload_sha256") != prompt_contract.get("payload_sha256"):
                        errors.append("prompt contract payload SHA-256 mismatch")
                    source_prompt = contract.get("source_prompt")
                    if not isinstance(source_prompt, dict):
                        errors.append("bound prompt contract source_prompt missing")
                    elif source_prompt.get("sha256") != prompt_contract.get("source_prompt_sha256"):
                        errors.append("source prompt SHA-256 binding mismatch")

                    for field, category in TARGET_CATEGORIES.items():
                        values = contract.get(field)
                        if not isinstance(values, list):
                            errors.append(f"bound prompt contract {field} must be a list")
                            continue
                        for item in values:
                            if not isinstance(item, dict):
                                errors.append(
                                    f"bound prompt contract {field} item must be a mapping"
                                )
                                continue
                            obligation_id = item.get("obligation_id")
                            if not non_empty(obligation_id):
                                errors.append(
                                    f"bound prompt contract {field} obligation_id missing"
                                )
                                continue
                            if obligation_id in expected_obligations:
                                errors.append(
                                    f"duplicate bound contract obligation_id: {obligation_id}"
                                )
                            expected_obligations[obligation_id] = category

    evidence_raw = packet.get("evidence_manifest")
    evidence_ids: set[str] = set()
    evidence_records: dict[str, dict[str, Any]] = {}
    if not isinstance(evidence_raw, list) or not evidence_raw:
        errors.append("evidence_manifest must be a non-empty list")
        evidence_raw = []
    for index, item in enumerate(evidence_raw):
        if not isinstance(item, dict):
            errors.append(f"evidence_manifest[{index}] must be a mapping")
            continue
        evidence_id = item.get("evidence_id")
        if not non_empty(evidence_id):
            errors.append(f"evidence_manifest[{index}].evidence_id missing")
            continue
        if evidence_id in evidence_ids:
            errors.append(f"duplicate evidence_id: {evidence_id}")
            continue
        evidence_ids.add(evidence_id)
        evidence_records[evidence_id] = item

    if not template_mode:
        for evidence_id, item in evidence_records.items():
            path_value = item.get("path")
            if not non_empty(path_value):
                errors.append(f"evidence {evidence_id} path missing")
                continue
            require_hash(item.get("sha256"), f"evidence {evidence_id} sha256", errors)
            try:
                evidence_path = safe_under(root, path_value, f"evidence {evidence_id}")
            except ValueError as exc:
                errors.append(str(exc))
                continue
            if not evidence_path.is_file():
                errors.append(f"evidence file missing: {path_value}")
            elif sha256_file(evidence_path) != item.get("sha256"):
                errors.append(f"evidence SHA-256 mismatch: {evidence_id}")

        report_path_value = packet.get("report_path")
        if non_empty(report_path_value):
            try:
                report_path = safe_under(root, report_path_value, "report_path")
            except ValueError as exc:
                errors.append(str(exc))
            else:
                if not report_path.is_file():
                    errors.append("completion report file missing")
                elif sha256_file(report_path) != packet.get("report_sha256"):
                    errors.append("completion report SHA-256 mismatch")
                if not any(
                    item.get("path") == report_path_value for item in evidence_records.values()
                ):
                    errors.append("completion report must be present in evidence_manifest")

    requirement_results = packet.get("requirement_results")
    if not isinstance(requirement_results, list) or not requirement_results:
        errors.append("requirement_results must be a non-empty list")
        requirement_results = []
    seen_requirements: set[str] = set()
    actual_requirements: dict[str, str] = {}
    valid_categories = set(TARGET_CATEGORIES.values())
    for index, item in enumerate(requirement_results):
        if not isinstance(item, dict):
            errors.append(f"requirement_results[{index}] must be a mapping")
            continue
        obligation_id = item.get("obligation_id")
        category = item.get("category")
        if not non_empty(obligation_id):
            errors.append(f"requirement_results[{index}].obligation_id missing")
            continue
        if obligation_id in seen_requirements:
            errors.append(f"duplicate requirement obligation_id: {obligation_id}")
            continue
        seen_requirements.add(obligation_id)
        if category not in valid_categories:
            errors.append(f"invalid requirement category for {obligation_id}")
        else:
            actual_requirements[obligation_id] = category
        if item.get("result") != "satisfied":
            errors.append(f"required obligation not satisfied: {obligation_id}")
        refs = item.get("evidence_ids")
        if not isinstance(refs, list) or not refs:
            errors.append(f"requirement {obligation_id} must reference evidence")
        else:
            for ref in refs:
                if ref not in evidence_ids:
                    errors.append(f"unknown evidence reference for {obligation_id}: {ref}")

    if not template_mode and contract is not None:
        missing = sorted(set(expected_obligations) - set(actual_requirements))
        unknown = sorted(set(actual_requirements) - set(expected_obligations))
        if missing:
            errors.append("missing prompt-contract obligation results: " + ",".join(missing))
        if unknown:
            errors.append("unknown prompt-contract obligation results: " + ",".join(unknown))
        for obligation_id in sorted(set(expected_obligations) & set(actual_requirements)):
            if expected_obligations[obligation_id] != actual_requirements[obligation_id]:
                errors.append(
                    f"requirement category mismatch for {obligation_id}: "
                    f"{actual_requirements[obligation_id]} != "
                    f"{expected_obligations[obligation_id]}"
                )

    checks = packet.get("checks")
    if not isinstance(checks, dict):
        errors.append("checks must be a mapping")
        checks = {}
    for key in REQUIRED_CHECKS:
        value = checks.get(key)
        ok = value in OK if isinstance(value, (str, bool)) else False
        if not ok and isinstance(value, str):
            ok = value.strip().lower() in OK
        if key not in checks:
            errors.append(f"checks.{key} is required")
        elif not ok:
            errors.append(f"checks.{key} is not successful")
    failed = checks.get("check_report_failed")
    if failed is not None and (not isinstance(failed, int) or failed != 0):
        errors.append("checks.check_report_failed must be integer 0")
    warnings_count = checks.get("check_report_warnings")
    if warnings_count is not None and not isinstance(warnings_count, int):
        errors.append("checks.check_report_warnings must be an integer")

    check_results = packet.get("check_results")
    if not isinstance(check_results, list) or not check_results:
        errors.append("check_results must be a non-empty list")
        check_results = []
    seen_checks: set[str] = set()
    for index, item in enumerate(check_results):
        if not isinstance(item, dict):
            errors.append(f"check_results[{index}] must be a mapping")
            continue
        check_id = item.get("check_id")
        if not non_empty(check_id):
            errors.append(f"check_results[{index}].check_id missing")
            continue
        if check_id in seen_checks:
            errors.append(f"duplicate check_id: {check_id}")
        seen_checks.add(check_id)
        if not non_empty(item.get("command")):
            errors.append(f"check {check_id} command missing")
        if item.get("result") != "passed":
            errors.append(f"check result not passed: {check_id}")
        refs = item.get("evidence_ids")
        if not isinstance(refs, list) or not refs:
            errors.append(f"check {check_id} must reference evidence")
        else:
            for ref in refs:
                if ref not in evidence_ids:
                    errors.append(f"unknown evidence reference for check {check_id}: {ref}")

    boundaries = packet.get("boundary_confirmations")
    if not isinstance(boundaries, dict):
        errors.append("boundary_confirmations must be a mapping")
        boundaries = {}
    for key in (
        "automatic_acceptance_performed",
        "automatic_return_performed",
        "historical_evidence_rewritten",
        "prompt_contract_mutated",
        "rollout_or_production_write_performed",
    ):
        if boundaries.get(key) is not False:
            errors.append(f"boundary_confirmations.{key} must be false")
    if boundaries.get("module_write_scope_respected") is not True:
        errors.append("boundary_confirmations.module_write_scope_respected must be true")

    semantic = packet.get("semantic_fidelity")
    if not isinstance(semantic, dict):
        errors.append("semantic_fidelity must be a mapping")
        semantic = {}
    if semantic.get("module_attests_requirement_results_complete") is not True:
        errors.append("module requirement-results attestation must be true")
    if semantic.get("human_blueprint_review_required") is not True:
        errors.append("human Blueprint semantic review must remain required")
    if semantic.get("execution_fingerprint_sufficient") is not False:
        errors.append("execution fingerprint must not be complete fidelity proof")

    publication = packet.get("publication")
    if not isinstance(publication, dict):
        errors.append("publication must be a mapping")
        publication = {}
    for key in (
        "completion_commit_embedded",
        "remote_containment_claimed_by_packet",
        "automatic_commit",
        "automatic_push",
    ):
        if publication.get(key) is not False:
            errors.append(f"publication.{key} must be false")
    if publication.get("external_publication_verification_required") is not True:
        errors.append("publication.external_publication_verification_required must be true")

    revision = packet.get("revision")
    if not isinstance(revision, dict):
        errors.append("revision must be a mapping")
        revision = {}
    values = [
        revision.get("supersedes_completion_id"),
        revision.get("supersedes_packet_path"),
        revision.get("revision_reason"),
    ]
    populated = [value is not None for value in values]
    if any(populated) and not all(populated):
        errors.append("superseding packet fields must be provided together")
    if all(populated):
        for key, value in zip(
            ("supersedes_completion_id", "supersedes_packet_path", "revision_reason"),
            values,
            strict=True,
        ):
            if not non_empty(value):
                errors.append(f"revision.{key} must be a non-empty string when superseding")

    promotion = packet.get("promotion")
    if not isinstance(promotion, dict):
        errors.append("promotion must be a mapping")
        promotion = {}
    if promotion.get("state") != "candidate_reference_only":
        errors.append("promotion.state must remain candidate_reference_only")
    if promotion.get("normal_acceptance_allowed") is not False:
        errors.append("promotion.normal_acceptance_allowed must remain false")
    if promotion.get("promotion_performed") is not False:
        errors.append("STEP22 must not perform global v0.4 promotion")

    integrity = packet.get("integrity")
    if not isinstance(integrity, dict):
        errors.append("integrity must be a mapping")
        integrity = {}
    if integrity.get("algorithm") != "sha256":
        errors.append("integrity.algorithm must be sha256")
    payload_hash = integrity.get("payload_sha256")
    if template_mode:
        if not non_empty(payload_hash):
            errors.append("integrity.payload_sha256 missing")
    else:
        require_hash(payload_hash, "integrity.payload_sha256", errors)
        if (
            isinstance(payload_hash, str)
            and HEX64.fullmatch(payload_hash)
            and canonical_payload_sha256(packet) != payload_hash
        ):
            errors.append("completion packet payload SHA-256 mismatch")

    return {
        "schema_version": "completion_packet_v0_4_validation_report_v0_1",
        "packet_path": str(packet_path),
        "template_mode": template_mode,
        "result": "PASSED" if not errors else "FAILED",
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "requirement_results": len(requirement_results),
            "check_results": len(check_results),
            "evidence_items": len(evidence_records),
            "bound_contract_obligations": len(expected_obligations),
        },
        "promotion": {
            "state": promotion.get("state"),
            "normal_acceptance_allowed": promotion.get("normal_acceptance_allowed"),
            "promotion_performed": promotion.get("promotion_performed"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--packet", required=True)
    parser.add_argument("--template-mode", action="store_true")
    parser.add_argument("--output-format", choices=("text", "yaml"), default="text")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    packet_path = safe_under(root, args.packet, "packet")
    report = validate_packet(
        root,
        packet_path,
        template_mode=args.template_mode,
    )

    if args.output_format == "yaml":
        print(yaml.safe_dump(report, sort_keys=False, allow_unicode=True).rstrip())
    else:
        print("ForPrint Completion Packet v0.4 validation")
        print(f"packet: {args.packet}")
        print(f"template_mode: {str(args.template_mode).lower()}")
        print(f"result: {report['result']}")
        print(f"errors: {','.join(report['errors']) or '-'}")
        print(f"warnings: {','.join(report['warnings']) or '-'}")
        for key, value in report["summary"].items():
            print(f"{key}: {value}")
        print(
            "candidate/reference-only: "
            f"{report['promotion']['state'] == 'candidate_reference_only'}"
        )
        print(f"normal_acceptance_allowed: {report['promotion']['normal_acceptance_allowed']}")
        print(f"promotion_performed: {report['promotion']['promotion_performed']}")
    return 0 if report["result"] == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
