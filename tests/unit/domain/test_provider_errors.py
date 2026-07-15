import pytest

from app.domain import (
    ProviderError,
    ProviderErrorCode,
    ProviderOperation,
)

REQUIRED_ERROR_CODES = {
    "invalid_request",
    "unsupported_capability",
    "recipient_validation_failed",
    "address_validation_failed",
    "provider_configuration_unavailable",
    "provider_authentication_unavailable",
    "provider_temporarily_unavailable",
    "provider_rate_limited",
    "provider_response_invalid",
    "tracking_reference_invalid",
    "live_write_disabled",
    "unexpected_provider_error",
}


def test_error_taxonomy_contains_required_codes() -> None:
    assert {item.value for item in ProviderErrorCode} == REQUIRED_ERROR_CODES


def test_retryability_is_explicit() -> None:
    temporary = ProviderError.from_code(ProviderErrorCode.PROVIDER_TEMPORARILY_UNAVAILABLE)
    rate_limited = ProviderError.from_code(ProviderErrorCode.PROVIDER_RATE_LIMITED)
    invalid = ProviderError.from_code(ProviderErrorCode.INVALID_REQUEST)

    assert temporary.retryable is True
    assert rate_limited.retryable is True
    assert invalid.retryable is False


def test_safe_render_excludes_metadata_values() -> None:
    error = ProviderError.from_code(
        ProviderErrorCode.PROVIDER_RESPONSE_INVALID,
        provider_id="synthetic_parcel",
        operation=ProviderOperation.TRACKING_LOOKUP,
        metadata=(("response_code", "SYNTHETIC-500"),),
    )

    output = error.render_safe()

    assert "provider_response_invalid" in output
    assert "synthetic_parcel" in output
    assert "tracking_lookup" in output
    assert "SYNTHETIC-500" not in output


def test_sensitive_error_metadata_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="Sensitive provider metadata",
    ):
        ProviderError.from_code(
            ProviderErrorCode.UNEXPECTED_PROVIDER_ERROR,
            metadata=(("authorization_token", "unsafe"),),
        )
