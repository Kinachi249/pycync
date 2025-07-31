from __future__ import annotations
from typing import TYPE_CHECKING

from abc import abstractmethod
from typing import Protocol

from pycync.devices.capabilities import CyncCapability

if TYPE_CHECKING:
    from pycync.devices.groups import CyncHome


class CyncControllable(Protocol):
    """Protocol describing any Cync entity that can be controlled by the user."""

    parent_home: CyncHome

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
