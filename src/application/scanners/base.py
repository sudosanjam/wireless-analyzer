"""
Base Scanner Backend abstraction and interface metadata.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from application.models.observation import RawObservation


@dataclass
class InterfaceInfo:
    name: str
    interface_type: str        # "wifi" | "ble" | "mock"
    is_up: bool = True
    mac_address: str | None = None
    driver: str | None = None
    chipset: str | None = None
    supports_monitor_mode: bool = False
    supported_bands: list[str] = field(default_factory=list)


class BaseScannerBackend(ABC):
    """Abstract interface for all hardware observation backends."""

    def __init__(self, interface: str = "auto", config: dict[str, Any] | None = None) -> None:
        self.interface = interface
        self.config = config or {}
        self.is_running = False

    @abstractmethod
    def is_available(self) -> bool:
        """Check if required system tools and hardware for this backend are present."""
        pass

    @abstractmethod
    def start(self) -> None:
        """Initialize and start scanner."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop scanner and release hardware/subprocess resources."""
        pass

    @abstractmethod
    def scan(self) -> list[RawObservation]:
        """Perform one observation cycle and return list of raw observations."""
        pass
