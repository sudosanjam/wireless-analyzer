"""
Raw and Normalized Observation models.
"""

from dataclasses import dataclass, field
from typing import Any
import uuid
import time


@dataclass
class RawObservation:
    """Raw un-normalized output directly from a scanner backend."""
    source: str                    # "wifi" | "ble" | "mock"
    interface: str                 # "wlan0", "hci0", "mock-0"
    raw_identifier: str            # MAC or raw address string
    timestamp: float = field(default_factory=time.time)
    ssid: str | None = None
    device_name: str | None = None
    rssi: int | None = None
    channel: int | None = None
    frequency: int | None = None
    security: str | None = None
    capabilities: list[str] = field(default_factory=list)
    service_uuids: list[str] = field(default_factory=list)
    manufacturer_raw: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedObservation:
    """Fully normalized, sanitized, categorized observation."""
    source: str                          # "wifi" | "ble" | "mock"
    interface: str                       # e.g., "wlan0"
    mac_address: str                     # XX:XX:XX:XX:XX:XX
    is_randomized: bool                  # True if IEEE Locally Administered bit is 1
    rssi: int                            # dBm value (e.g. -65)
    rssi_category: str                   # "STRONG", "MEDIUM", "WEAK"
    timestamp: float = field(default_factory=time.time)
    observation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    ssid: str | None = None
    bssid: str | None = None
    device_name: str | None = None
    channel: int | None = None
    frequency: int | None = None
    band: str | None = None              # "2.4 GHz", "5 GHz", "6 GHz", "BLE 2.4 GHz"
    security: str | None = None
    capabilities: list[str] = field(default_factory=list)
    service_uuids: list[str] = field(default_factory=list)
    manufacturer: str = "Unknown"
    oui: str | None = None
    device_category: str = "UNKNOWN"
    classification_confidence: float = 0.0
    classification_reason: str = "Unclassified"
    classification_evidence: list[str] = field(default_factory=list)
    priority: str = "INFO"               # "INFO", "LOW", "MEDIUM", "HIGH"
    watchlist_matched: bool = False
    watchlist_notes: list[str] = field(default_factory=list)
    raw_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert normalized observation to serializable dictionary."""
        return {
            "observation_id": self.observation_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "source": self.source,
            "interface": self.interface,
            "mac_address": self.mac_address,
            "is_randomized": self.is_randomized,
            "ssid": self.ssid,
            "bssid": self.bssid,
            "device_name": self.device_name,
            "rssi": self.rssi,
            "rssi_category": self.rssi_category,
            "channel": self.channel,
            "frequency": self.frequency,
            "band": self.band,
            "security": self.security,
            "capabilities": self.capabilities,
            "service_uuids": self.service_uuids,
            "manufacturer": self.manufacturer,
            "oui": self.oui,
            "device_category": self.device_category,
            "classification_confidence": self.classification_confidence,
            "classification_reason": self.classification_reason,
            "classification_evidence": self.classification_evidence,
            "priority": self.priority,
            "watchlist_matched": self.watchlist_matched,
            "watchlist_notes": self.watchlist_notes,
            "raw_metadata": self.raw_metadata,
        }
