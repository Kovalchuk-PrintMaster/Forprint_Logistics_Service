from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from app.adapters.providers.base import ProviderAdapter
from app.domain.provider_contracts import (
    ProviderCapabilityDescription,
)
from app.domain.providers import ProviderCapability


class DuplicateProviderRegistrationError(ValueError):
    """Raised when a provider ID is registered more than once."""


class ProviderNotRegisteredError(LookupError):
    """Raised when a provider ID is absent from the registry."""


class ProviderDisabledError(LookupError):
    """Raised when normal lookup targets a disabled provider."""


def normalize_provider_id(provider_id: str) -> str:
    """Normalize a provider identifier for deterministic lookup."""

    normalized = provider_id.strip().casefold()

    if not normalized:
        raise ValueError("provider_id must not be empty")

    return normalized


@dataclass(frozen=True, slots=True)
class ProviderRegistryDescription:
    """Safe registry view without adapter or credential objects."""

    provider_id: str
    display_name: str
    enabled: bool
    source: str
    capability_description: ProviderCapabilityDescription
    live_write_enabled: bool = False

    def __post_init__(self) -> None:
        provider_id = self.provider_id.strip()
        display_name = self.display_name.strip()
        source = self.source.strip()

        if not provider_id:
            raise ValueError("provider_id must not be empty")

        if not display_name:
            raise ValueError("display_name must not be empty")

        if not source:
            raise ValueError("source must not be empty")

        if self.live_write_enabled:
            raise ValueError("Live provider writes must remain disabled")

        if self.capability_description.provider_id != provider_id:
            raise ValueError("Capability description provider mismatch")

        object.__setattr__(
            self,
            "provider_id",
            provider_id,
        )
        object.__setattr__(
            self,
            "display_name",
            display_name,
        )
        object.__setattr__(
            self,
            "source",
            source,
        )

    def supports(
        self,
        capability: ProviderCapability,
    ) -> bool:
        return self.capability_description.support_for(capability).supported


@dataclass(frozen=True, slots=True)
class ProviderRegistryEntry:
    """Internal registry entry retaining the adapter instance."""

    adapter: ProviderAdapter = field(repr=False)
    enabled: bool = False
    source: str = "local_contract_registration"

    def __post_init__(self) -> None:
        source = self.source.strip()

        if not source:
            raise ValueError("source must not be empty")

        object.__setattr__(
            self,
            "source",
            source,
        )

    @property
    def provider_id(self) -> str:
        return self.adapter.provider.provider_id

    def describe(self) -> ProviderRegistryDescription:
        provider = self.adapter.provider

        return ProviderRegistryDescription(
            provider_id=provider.provider_id,
            display_name=provider.display_name,
            enabled=self.enabled,
            source=self.source,
            capability_description=(self.adapter.describe_capabilities()),
            live_write_enabled=False,
        )


class ProviderRegistry:
    """Process-local provider adapter registry.

    Registration is explicit. Providers are disabled by default.
    The registry does not load credentials, perform provider calls,
    auto-enable providers or select a provider by business price.
    """

    def __init__(
        self,
        entries: Iterable[ProviderRegistryEntry] = (),
    ) -> None:
        self._entries: dict[
            str,
            ProviderRegistryEntry,
        ] = {}

        for entry in entries:
            self.register(
                entry.adapter,
                enabled=entry.enabled,
                source=entry.source,
            )

    def register(
        self,
        adapter: ProviderAdapter,
        *,
        enabled: bool = False,
        source: str = "local_contract_registration",
    ) -> ProviderRegistryEntry:
        provider_id = adapter.provider.provider_id
        key = normalize_provider_id(provider_id)

        if key in self._entries:
            raise DuplicateProviderRegistrationError(
                f"Provider is already registered: {provider_id}"
            )

        entry = ProviderRegistryEntry(
            adapter=adapter,
            enabled=enabled,
            source=source,
        )
        self._entries[key] = entry

        return entry

    def get(
        self,
        provider_id: str,
    ) -> ProviderRegistryEntry | None:
        return self._entries.get(normalize_provider_id(provider_id))

    def resolve(
        self,
        provider_id: str,
        *,
        include_disabled: bool = False,
    ) -> ProviderAdapter:
        entry = self.get(provider_id)

        if entry is None:
            raise ProviderNotRegisteredError(f"Provider is not registered: {provider_id.strip()}")

        if not entry.enabled and not include_disabled:
            raise ProviderDisabledError(f"Provider is registered but disabled: {entry.provider_id}")

        return entry.adapter

    def describe(
        self,
        provider_id: str,
    ) -> ProviderRegistryDescription:
        entry = self.get(provider_id)

        if entry is None:
            raise ProviderNotRegisteredError(f"Provider is not registered: {provider_id.strip()}")

        return entry.describe()

    def list_descriptions(
        self,
        *,
        include_disabled: bool = True,
    ) -> tuple[ProviderRegistryDescription, ...]:
        descriptions = (
            entry.describe()
            for entry in self._entries.values()
            if include_disabled or entry.enabled
        )

        return tuple(
            sorted(
                descriptions,
                key=lambda item: item.provider_id,
            )
        )

    def filter_by_capability(
        self,
        capability: ProviderCapability,
        *,
        include_disabled: bool = False,
    ) -> tuple[ProviderRegistryDescription, ...]:
        return tuple(
            description
            for description in self.list_descriptions(include_disabled=include_disabled)
            if description.supports(capability)
        )

    def provider_ids(
        self,
        *,
        include_disabled: bool = True,
    ) -> tuple[str, ...]:
        return tuple(
            description.provider_id
            for description in self.list_descriptions(include_disabled=include_disabled)
        )

    def __len__(self) -> int:
        return len(self._entries)
