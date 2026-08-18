from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path
from typing import Any

import yaml

EXPECTED_SCHEMA = "module_completion_outbox_event_v0_4"
EXPECTED_PROTOCOL = "module_completion_outbox_protocol_v0_4"
EXPECTED_EVENT_TYPE = "module_completion_published_v0_4"
EXPECTED_STATUS = "published_pending_blueprint_discovery"
OUTBOX = "coordination/completion_outbox/records"
PACKETS = "coordination/completion_packets/records"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def load(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected YAML mapping: {path}")
    return data


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _registered_module(
    registry: dict[str, Any],
    module_id: str,
) -> dict[str, Any] | None:
    modules = registry.get("modules", [])
    if not isinstance(modules, list):
        return None
    rows = [x for x in modules if isinstance(x, dict) and x.get("module_id") == module_id]
    return rows[0] if len(rows) == 1 else None


def validate_outbox_event(
    path: Path,
    *,
    root: Path,
    registry_path: Path,
    template_mode: bool = False,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        event = load(path)
    except Exception as exc:
        return {
            "result": "FAILED",
            "errors": [f"cannot load event: {exc}"],
            "warnings": [],
        }

    if event.get("schema_version") != EXPECTED_SCHEMA:
        errors.append("schema_version mismatch")
    if event.get("protocol_version") != EXPECTED_PROTOCOL:
        errors.append("protocol_version mismatch")
    if event.get("event_type") != EXPECTED_EVENT_TYPE:
        errors.append("event_type mismatch")
    if event.get("status") != EXPECTED_STATUS:
        errors.append("status mismatch")
    if event.get("immutable") is not True:
        errors.append("immutable must be true")

    for key in [
        "event_id",
        "module_id",
        "repository_id",
        "prompt_id",
        "completion_id",
        "emitted_at",
    ]:
        if not _nonempty(event.get(key)):
            errors.append(f"{key} must be a non-empty string")

    event_id = event.get("event_id")
    completion_id = event.get("completion_id")
    module_id = event.get("module_id")
    repository_id = event.get("repository_id")
    prompt_id = event.get("prompt_id")

    if not template_mode and _nonempty(event_id) and path.name != f"{event_id}.yaml":
        errors.append("immutable outbox event instance filename mismatch")

    packet = event.get("completion_packet")
    if not isinstance(packet, dict):
        errors.append("completion_packet must be a mapping")
        packet = {}

    expected_packet_rel = f"{PACKETS}/{completion_id}.yaml" if _nonempty(completion_id) else None
    if expected_packet_rel and packet.get("path") != expected_packet_rel:
        errors.append("completion_packet.path mismatch")
    packet_sha = packet.get("sha256")
    if not isinstance(packet_sha, str) or not HEX64.fullmatch(packet_sha):
        errors.append("completion_packet.sha256 must be 64 lowercase hex")

    try:
        registry = load(registry_path)
    except Exception as exc:
        errors.append(f"cannot load coordination source registry: {exc}")
        registry = {}

    policy = registry.get("lookup_policy", {})
    if policy.get("completion_outbox_authority") != "module_owned":
        errors.append("registry completion_outbox_authority must be module_owned")
    if policy.get("completion_outbox_future_path") != OUTBOX:
        errors.append("registry completion_outbox_future_path mismatch")
    if policy.get("module_repository_access") != "read_only_from_blueprint":
        errors.append("registry module_repository_access mismatch")

    if _nonempty(module_id):
        module = _registered_module(registry, module_id)
        if module is None:
            errors.append("module_id is not uniquely registered")
        else:
            repo = module.get("repository", {})
            outbox = module.get("sources", {}).get("completion_outbox", {})
            bounds = module.get("boundaries", {})
            if repo.get("repository_id") != repository_id:
                errors.append("repository_id does not match registry")
            if outbox.get("owner") != module_id:
                errors.append("registry outbox owner does not match module_id")
            if outbox.get("path") != OUTBOX:
                errors.append("registry outbox path mismatch")
            if bounds.get("module_owns_completion_outbox") is not True:
                errors.append("registry module_owns_completion_outbox must be true")
            if bounds.get("blueprint_lookup_mode") != "read_only":
                errors.append("registry blueprint_lookup_mode must be read_only")

    if not template_mode and expected_packet_rel:
        packet_file = root / expected_packet_rel
        if not packet_file.is_file():
            errors.append("referenced Completion Packet v0.4 does not exist")
        else:
            if (
                isinstance(packet_sha, str)
                and HEX64.fullmatch(packet_sha)
                and file_sha256(packet_file) != packet_sha
            ):
                errors.append("completion_packet.sha256 does not match file")
            try:
                packet_data = load(packet_file)
            except Exception as exc:
                errors.append(f"cannot load referenced completion packet: {exc}")
                packet_data = {}
            if packet_data:
                if packet_data.get("schema_version") != "module_completion_packet_v0_4":
                    errors.append("referenced completion packet schema mismatch")
                if packet_data.get("completion_id") != completion_id:
                    errors.append("completion_id does not match completion packet")
                if packet_data.get("module_id") != module_id:
                    errors.append("module_id does not match completion packet")
                if packet_data.get("prompt_id") != prompt_id:
                    errors.append("prompt_id does not match completion packet")

    publication = event.get("publication")
    if not isinstance(publication, dict):
        errors.append("publication must be a mapping")
        publication = {}

    commit = publication.get("completion_subject_commit")
    if not isinstance(commit, str) or not HEX40.fullmatch(commit):
        errors.append("publication.completion_subject_commit must be full 40-char lowercase hex")

    for key in ["remote_name", "branch", "verified_at", "verification_evidence_path"]:
        if not _nonempty(publication.get(key)):
            errors.append(f"publication.{key} must be a non-empty string")

    evidence_sha = publication.get("verification_evidence_sha256")
    if not isinstance(evidence_sha, str) or not HEX64.fullmatch(evidence_sha):
        errors.append("publication.verification_evidence_sha256 must be 64 lowercase hex")

    if publication.get("remote_containment_verified") is not True:
        errors.append("publication.remote_containment_verified must be true")
    if publication.get("outbox_event_commit_embedded_in_event") is not False:
        errors.append("publication.outbox_event_commit_embedded_in_event must be false")
    if publication.get("external_outbox_event_publication_verification_required") is not True:
        errors.append(
            "publication.external_outbox_event_publication_verification_required must be true"
        )
    for key in ["automatic_commit", "automatic_push"]:
        if publication.get(key) is not False:
            errors.append(f"publication.{key} must be false")

    evidence_path_value = publication.get("verification_evidence_path")
    if not template_mode and _nonempty(evidence_path_value):
        evidence_file = root / evidence_path_value
        if not evidence_file.is_file():
            errors.append("publication verification evidence file does not exist")
        elif (
            isinstance(evidence_sha, str)
            and HEX64.fullmatch(evidence_sha)
            and file_sha256(evidence_file) != evidence_sha
        ):
            errors.append("publication.verification_evidence_sha256 does not match file")

    revision = event.get("revision")
    if not isinstance(revision, dict):
        errors.append("revision must be a mapping")
        revision = {}

    revision_fields = [
        revision.get("supersedes_event_id"),
        revision.get("supersedes_event_path"),
        revision.get("revision_reason"),
    ]
    provided = [x is not None for x in revision_fields]
    if any(provided) and not all(provided):
        errors.append("superseding event fields must be provided together")
    if all(provided):
        sid, spath, reason = revision_fields
        for key, value in [
            ("supersedes_event_id", sid),
            ("supersedes_event_path", spath),
            ("revision_reason", reason),
        ]:
            if not _nonempty(value):
                errors.append(f"revision.{key} must be a non-empty string when superseding")
        if _nonempty(sid) and spath != f"{OUTBOX}/{sid}.yaml":
            errors.append("revision.supersedes_event_path must be canonical")
        if _nonempty(event_id) and sid == event_id:
            errors.append("outbox event cannot supersede itself")

    governance = event.get("governance")
    if not isinstance(governance, dict):
        errors.append("governance must be a mapping")
        governance = {}
    for key in [
        "blueprint_discovery_performed",
        "blueprint_intake_performed",
        "operator_decision_created",
        "global_v0_4_promotion_performed",
    ]:
        if governance.get(key) is not False:
            errors.append(f"governance.{key} must be false")

    return {
        "schema_version": "completion_outbox_v0_4_validation_report_v0_1",
        "event": str(path),
        "template_mode": template_mode,
        "result": "PASSED" if not errors else "FAILED",
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("event", type=Path)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("coordination/registry/coordination_source_registry_v0_1.yaml"),
    )
    parser.add_argument("--template", action="store_true")
    args = parser.parse_args()

    report = validate_outbox_event(
        args.event,
        root=args.root,
        registry_path=args.registry,
        template_mode=args.template,
    )

    print("ForPrint Completion Outbox v0.4 validation")
    print(f"event: {args.event}")
    print(f"template_mode: {args.template}")
    print(f"result: {report['result']}")
    print("errors:")
    if report["errors"]:
        for item in report["errors"]:
            print(f"  - {item}")
    else:
        print("  -")
    print("warnings:")
    if report["warnings"]:
        for item in report["warnings"]:
            print(f"  - {item}")
    else:
        print("  -")
    print("candidate/reference-only: True")
    print("normal_acceptance_allowed: False")
    print("promotion_performed: False")
    return 0 if report["result"] == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
