"""
Environmental and System Event models.
"""

from dataclasses import dataclass, field
import time
from typing import Any
import uuid


@dataclass
class EnvironmentalEvent:
    """An event triggered by environmental changes or watchlist alerts."""
    session_id: str
    event_type: str                   # "NEW_CONTACT", "CONTACT_DEPARTED", "RSSI_SPIKE", "WATCHLIST_MATCH", "DENSITY_DELTA"
    severity: str = "INFO"            # "INFO", "LOW", "MEDIUM", "HIGH"
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    contact_id: str | None = None
    mac_address: str | None = None
    label: str = ""
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "severity": self.severity,
            "contact_id": self.contact_id,
            "mac_address": self.mac_address,
            "label": self.label,
            "message": self.message,
            "details": self.details,
        }
