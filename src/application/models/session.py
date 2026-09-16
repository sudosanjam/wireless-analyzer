"""
Session lifecycle model.
"""

from dataclasses import dataclass, field
import time
from typing import Any
import uuid


@dataclass
class Session:
    """Observation session metadata."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    interface: str = "auto"
    wifi_enabled: bool = True
    ble_enabled: bool = True
    scanner_backend: str = "auto"
    status: str = "RUNNING"     # "RUNNING", "COMPLETED", "INTERRUPTED"
    config_snapshot: dict[str, Any] = field(default_factory=dict)
    total_observations: int = 0
    unique_contacts: int = 0

    @property
    def duration_seconds(self) -> float:
        end = self.end_time if self.end_time is not None else time.time()
        return max(0.0, end - self.start_time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": round(self.duration_seconds, 1),
            "interface": self.interface,
            "wifi_enabled": self.wifi_enabled,
            "ble_enabled": self.ble_enabled,
            "scanner_backend": self.scanner_backend,
            "status": self.status,
            "total_observations": self.total_observations,
            "unique_contacts": self.unique_contacts,
            "config_snapshot": self.config_snapshot,
        }
