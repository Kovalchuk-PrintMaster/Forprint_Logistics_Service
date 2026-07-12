from datetime import UTC, datetime

from app.domain import TrackingRequest
from app.storage import (
    InMemoryLogisticsRepository,
)


def test_tracking_request_save_get_list() -> None:
    repository = InMemoryLogisticsRepository()
    request = TrackingRequest(
        provider_id="local_provider",
        tracking_number="LOCAL-TRACK-001",
        requested_at=datetime.now(UTC),
    )

    assert repository.save_tracking_request(request) is request
    assert (
        repository.get_tracking_request(
            "local_provider",
            "LOCAL-TRACK-001",
        )
        is request
    )
    assert repository.list_tracking_requests() == (request,)
