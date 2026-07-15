from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.domain.providers import ProviderOperation


class ProviderErrorCode(StrEnum):
    """Machine-readable provider-neutral error taxonomy."""

    INVALID_REQUEST = "invalid_request"
    UNSUPPORTED_CAPABILITY = "unsupported_capability"
    RECIPIENT_VALIDATION_FAILED = "recipient_validation_failed"
    ADDRESS_VALIDATION_FAILED = "address_validation_failed"
    PROVIDER_CONFIGURATION_UNAVAILABLE = "provider_configuration_unavailable"
    PROVIDER_AUTHENTICATION_UNAVAILABLE = "provider_authentication_unavailable"
    PROVIDER_TEMPORARILY_UNAVAILABLE = "provider_temporarily_unavailable"
    PROVIDER_RATE_LIMITED = "provider_rate_limited"
    PROVIDER_RESPONSE_INVALID = "provider_response_invalid"
    TRACKING_REFERENCE_INVALID = "tracking_reference_invalid"
    LIVE_WRITE_DISABLED = "live_write_disabled"
    UNEXPECTED_PROVIDER_ERROR = "unexpected_provider_error"


DEFAULT_SAFE_MESSAGES: dict[
    ProviderErrorCode,
    str,
] = {
    ProviderErrorCode.INVALID_REQUEST: "Provider request is invalid.",
    ProviderErrorCode.UNSUPPORTED_CAPABILITY: "Provider operation is not supported.",
    ProviderErrorCode.RECIPIENT_VALIDATION_FAILED: "Recipient validation failed.",
    ProviderErrorCode.ADDRESS_VALIDATION_FAILED: "Address validation failed.",
    ProviderErrorCode.PROVIDER_CONFIGURATION_UNAVAILABLE: "Provider configuration is unavailable.",
    ProviderErrorCode.PROVIDER_AUTHENTICATION_UNAVAILABLE: (
        "Provider authentication is unavailable."
    ),
    ProviderErrorCode.PROVIDER_TEMPORARILY_UNAVAILABLE: "Provider is temporarily unavailable.",
    ProviderErrorCode.PROVIDER_RATE_LIMITED: "Provider request was rate limited.",
    ProviderErrorCode.PROVIDER_RESPONSE_INVALID: "Provider returned an invalid response.",
    ProviderErrorCode.TRACKING_REFERENCE_INVALID: "Tracking reference is invalid.",
    ProviderErrorCode.LIVE_WRITE_DISABLED: "Live provider writes are disabled.",
    ProviderErrorCode.UNEXPECTED_PROVIDER_ERROR: "Unexpected provider error.",
}


RETRYABLE_ERROR_CODES = frozenset(
    {
        ProviderErrorCode.PROVIDER_TEMPORARILY_UNAVAILABLE,
        ProviderErrorCode.PROVIDER_RATE_LIMITED,
    }
)


SENSITIVE_KEY_MARKERS = (
    "access_token",
    "api_key",
    "api_token",
    "authorization",
    "credential",
    "password",
    "raw_response",
    "secret",
    "token",
)


def is_sensitive_key(value: str) -> bool:
    normalized = value.strip().casefold().replace("-", "_")

    return any(marker in normalized for marker in SENSITIVE_KEY_MARKERS)


@dataclass(frozen=True, slots=True)
class ProviderError:
    """Safe provider-neutral error for typed results."""

    code: ProviderErrorCode
    safe_message: str
    retryable: bool
    provider_id: str | None = None
    operation: ProviderOperation | None = None
    metadata: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        safe_message = self.safe_message.strip()

        if not safe_message:
            raise ValueError("safe_message must not be empty")

        if self.provider_id is not None and not self.provider_id.strip():
            raise ValueError("provider_id must not be empty")

        seen: set[str] = set()

        for key, _value in self.metadata:
            normalized_key = key.strip().casefold()

            if not normalized_key:
                raise ValueError("metadata key must not be empty")

            if normalized_key in seen:
                raise ValueError("metadata keys must be unique")

            if is_sensitive_key(normalized_key):
                raise ValueError("Sensitive provider metadata must not be exposed")

            seen.add(normalized_key)

        object.__setattr__(
            self,
            "safe_message",
            safe_message,
        )

        if self.provider_id is not None:
            object.__setattr__(
                self,
                "provider_id",
                self.provider_id.strip(),
            )

    @classmethod
    def from_code(
        cls,
        code: ProviderErrorCode,
        *,
        provider_id: str | None = None,
        operation: ProviderOperation | None = None,
        safe_message: str | None = None,
        metadata: tuple[
            tuple[str, str],
            ...,
        ] = (),
    ) -> ProviderError:
        return cls(
            code=code,
            safe_message=(safe_message or DEFAULT_SAFE_MESSAGES[code]),
            retryable=code in RETRYABLE_ERROR_CODES,
            provider_id=provider_id,
            operation=operation,
            metadata=metadata,
        )

    def render_safe(self) -> str:
        """Render without raw metadata or provider payloads."""

        parts = [
            self.code.value,
            self.safe_message,
            ("retryable" if self.retryable else "not_retryable"),
        ]

        if self.provider_id:
            parts.append(f"provider={self.provider_id}")

        if self.operation:
            parts.append(f"operation={self.operation.value}")

        return " | ".join(parts)
