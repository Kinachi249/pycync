from __future__ import annotations

from abc import abstractmethod
from typing import Protocol

from pycync.devices.capabilities import CyncCapability


class CyncControllable(Protocol):
    """Protocol describing any Cync entity that can be controlled by the user."""

    parent_home_id: int

    @property
    @abstractmethod
    def capabilities(self) -> frozenset[CyncCapability]:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def mesh_reference_id(self) -> int:
        pass

    @property
    @abstractmethod
    def unique_id(self) -> str:
        """Provides an identifier that uniquely identifies this controllable entity."""
        pass

    @abstractmethod
    def supports_capability(self, capability: CyncCapability) -> bool:
        pass
