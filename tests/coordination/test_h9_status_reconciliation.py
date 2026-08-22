from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
TRACKING_PROMPT_ID = "logistics_service_tracking_events_v0_1"
H9_REPORT_ID = "logistics_service_h9_reference_rollout_completion_v0_1"


def load_yaml(rel: str) -> dict:
    data = yaml.safe_load((ROOT / rel).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_tracking_events_current_records_observe_blueprint_acceptance() -> None:
    queue = load_yaml("coordination/blueprint_snapshot/prompt_queue.yaml")
    prompt_index = load_yaml("coordination/prompts/index.yaml")
    status = load_yaml("coordination/status/current_status.yaml")

    queue_row = next(row for row in queue["prompt_queue"] if row["prompt_id"] == TRACKING_PROMPT_ID)
    local_row = next(
        row for row in prompt_index["prompts"] if row["prompt_id"] == TRACKING_PROMPT_ID
    )

    assert queue_row["blueprint_review"]["status"] == "accepted_by_blueprint"
    assert queue_row["operator_decision"] == "ACCEPT"

    assert local_row["blueprint_review_status"] == "accepted_by_blueprint"
    assert local_row["blueprint_accepted_at"] == "2026-08-18"
    assert local_row["operator_decision"] == "ACCEPT"

    assert status["blueprint_review_status"] == "accepted_by_blueprint"
    assert status["acceptance_readiness"]["blueprint_acceptance_status"] == "accepted_by_blueprint"
    assert status["completion_evidence"]["blueprint_acceptance_status"] == "accepted_by_blueprint"
    assert status["completion_closeout"]["blueprint_acceptance_claimed"] is False
    assert status["automatic_acceptance"] is False


def test_h9_current_status_preserves_live_freshness_blocker() -> None:
    status = load_yaml("coordination/status/current_status.yaml")
    h9 = status["h9_coordination_rollout"]

    assert h9["result"] == (
        "H9_LOGISTICS_REFERENCE_ROLLOUT_IMPLEMENTED_DETERMINISTICALLY_"
        "LIVE_START_BLOCKED_BY_BLUEPRINT_REMOTE_FRESHNESS"
    )
    assert h9["live_start_executed"] is False
    assert h9["freshness_state"] == "STALE"
    assert h9["blueprint_repository_writes"] is False
    assert h9["business_prompt_release"] is False
    assert h9["business_prompt_claim"] is False
    assert h9["automatic_blueprint_acceptance"] is False
    assert h9["commit_performed"] is False
    assert h9["push_performed"] is False


def test_h9_report_is_indexed_without_business_prompt_packet() -> None:
    reports = load_yaml("coordination/reports/index.yaml")
    rows = [row for row in reports["reports"] if row.get("report_id") == H9_REPORT_ID]
    assert len(rows) == 1
    row = rows[0]
    assert row["type"] == "coordination_platform_rollout"
    assert row["prompt_id"] is None
    assert row["automatic_acceptance"] is False
    assert row["commit_performed"] is False
    assert row["push_performed"] is False

    report = ROOT / row["report_file"]
    assert report.is_file()
    text = report.read_text(encoding="utf-8")
    assert "H9_LIVE_START_BLOCKED_BY_BLUEPRINT_REMOTE_FRESHNESS" in text
    assert "Business prompt claim: `false`" in text
