from __future__ import annotations

from abc import ABC, abstractmethod
from typing import NoReturn, final

from app.domain.provider_contracts import (
    AddressValidationRequest,
    AddressValidationResult,
    DeliveryQuoteLookupRequest,
    DeliveryQuoteLookupResult,
    ProviderCapabilityDescription,
    RecipientValidationRequest,
    RecipientValidationResult,
    ShipmentPayloadPreviewRequest,
    ShipmentPayloadPreviewResult,
    TrackingLookupRequest,
    TrackingLookupResult,
)
from app.domain.provider_errors import (
    ProviderError,
    ProviderErrorCode,
)
from app.domain.providers import (
    LogisticsProvider,
    ProviderCapability,
    ProviderCapabilitySupport,
    ProviderOperation,
)
from app.domain.shipments import ShipmentDraft


class LiveProviderWriteDisabledError(RuntimeError):
    """Raised whenever code attempts a provider mutation."""

    def __init__(
        self,
        provider_error: ProviderError,
    ) -> None:
        self.provider_error = provider_error
        super().__init__(provider_error.render_safe())


class ProviderAdapter(ABC):
    """Single authoritative provider-neutral adapter boundary.

    Implementations expose typed validation, dry-run preview and
    read-only result contracts. Provider-side shipment creation
    remains structurally disabled.
    """

    @property
    @abstractmethod
    def provider(self) -> LogisticsProvider:
        """Return safe provider metadata without credentials."""

    def describe_capabilities(
        self,
    ) -> ProviderCapabilityDescription:
        """Return deterministic typed capability discovery."""

        return ProviderCapabilityDescription.from_provider(self.provider)

    def capability_support(
        self,
        capability: ProviderCapability,
    ) -> ProviderCapabilitySupport:
        """Return explicit supported or unsupported state."""

        return self.provider.capability_support(capability)

    def operation_support(
        self,
        operation: ProviderOperation,
    ) -> ProviderCapabilitySupport:
        """Resolve operation support deterministically."""

        return self.provider.operation_support(operation)

    def unsupported_operation_error(
        self,
        operation: ProviderOperation,
        *,
        safe_message: str | None = None,
    ) -> ProviderError:
        """Build a normalized unsupported-operation error."""

        code = (
            ProviderErrorCode.LIVE_WRITE_DISABLED
            if operation is ProviderOperation.LIVE_SHIPMENT_CREATION
            else ProviderErrorCode.UNSUPPORTED_CAPABILITY
        )

        return ProviderError.from_code(
            code,
            provider_id=self.provider.provider_id,
            operation=operation,
            safe_message=safe_message,
        )

    @abstractmethod
    def validate_recipient(
        self,
        request: RecipientValidationRequest,
    ) -> RecipientValidationResult:
        """Validate a recipient using a typed dry-run result."""

    @abstractmethod
    def validate_address(
        self,
        request: AddressValidationRequest,
    ) -> AddressValidationResult:
        """Validate an address using a typed dry-run result."""

    @abstractmethod
    def build_shipment_payload_preview(
        self,
        request: ShipmentPayloadPreviewRequest,
    ) -> ShipmentPayloadPreviewResult:
        """Build a typed non-mutating provider payload preview."""

    @abstractmethod
    def track(
        self,
        request: TrackingLookupRequest,
    ) -> TrackingLookupResult:
        """Return typed read-only tracking information."""

    def lookup_delivery_quote(
        self,
        request: DeliveryQuoteLookupRequest,
    ) -> DeliveryQuoteLookupResult:
        """Return explicit unavailability until implemented."""

        if request.provider_id != self.provider.provider_id:
            error = ProviderError.from_code(
                ProviderErrorCode.INVALID_REQUEST,
                provider_id=self.provider.provider_id,
                operation=(ProviderOperation.DELIVERY_QUOTE_LOOKUP),
                safe_message=("Delivery quote request provider does not match the adapter."),
            )
        else:
            error = self.unsupported_operation_error(
                ProviderOperation.DELIVERY_QUOTE_LOOKUP,
                safe_message=("Delivery quote lookup is not implemented for this adapter."),
            )

        return DeliveryQuoteLookupResult(
            provider_id=self.provider.provider_id,
            execution=request.execution,
            available=False,
            errors=(error,),
        )

    @final
    def create_shipment(
        self,
        draft: ShipmentDraft,
    ) -> NoReturn:
        """Reject every live provider shipment mutation."""

        del draft

        error = self.unsupported_operation_error(
            ProviderOperation.LIVE_SHIPMENT_CREATION,
            safe_message=(
                "Live provider shipment creation is disabled. "
                "A future approved checkpoint must add "
                "controlled safety gates."
            ),
        )

        raise LiveProviderWriteDisabledError(error)
