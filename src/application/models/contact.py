"""
Correlated Contact entity model with temporal state management.
"""

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import time
from typing import Any
import uuid


class ContactState(str, Enum):
    NEW = "NEW"          # First observed in current session
    ACTIVE = "ACTIVE"    # Observed during most recent scan interval
    RECENT = "RECENT"    # Observed within recent threshold, fading
    STALE = "STALE"      # Not seen for stale threshold, dimmed


@dataclass
class CorrelatedContact:
    """
    A persistent or tracked wireless contact correlated over time.
    Tracks state machine, smoothed signal telemetry, and deterministic display coordinates.
    """
    normalized_identifier: str       # MAC or stable identifier
    signal_type: str                 # "wifi" | "ble" | "mock"
    session_id: str
    contact_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    mac_address: str = ""
    is_randomized: bool = False
    ssid: str | None = None
    device_name: str | None = None
    state: ContactState = ContactState.NEW
    
    # RSSI telemetry
    latest_rssi: int = -90
    smoothed_rssi: float = -90.0
    min_rssi: int = -90
    max_rssi: int = -90
    rssi_category: str = "WEAK"
    
    # Wireless characteristics
    channel: int | None = None
    frequency: int | None = None
    band: str | None = None
    security: str | None = None
    capabilities: list[str] = field(default_factory=list)
    service_uuids: list[str] = field(default_factory=list)
    
    # Classification & Identity
    manufacturer: str = "Unknown"
    oui: str | None = None
    device_category: str = "UNKNOWN"
    classification_confidence: float = 0.0
    classification_reason: str = "Unclassified"
    classification_evidence: list[str] = field(default_factory=list)
    priority: str = "INFO"
    watchlist_matched: bool = False
    watchlist_notes: list[str] = field(default_factory=list)
    
    # Temporal metrics
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    observation_count: int = 1
    last_state_change: float = field(default_factory=time.time)
    
    # Deterministic visualization positioning
    # Note: Radar position is a visual hash representation, not physical bearing
    radar_angle_degrees: float = 0.0
    radar_distance_ratio: float = 0.5

    def __post_init__(self) -> None:
        if not self.mac_address:
            self.mac_address = self.normalized_identifier
        self.smoothed_rssi = float(self.latest_rssi)
        self.min_rssi = self.latest_rssi
        self.max_rssi = self.latest_rssi
        self._calculate_deterministic_radar_coords()

    def _calculate_deterministic_radar_coords(self) -> None:
        """Calculate stable angle based on SHA-256 hash of identifier."""
        raw_hash = hashlib.sha256(self.normalized_identifier.encode("utf-8")).hexdigest()
        angle_int = int(raw_hash[:8], 16)
        self.radar_angle_degrees = float(angle_int % 360)
        self.update_radar_distance()

    def update_radar_distance(self, rssi_min: int = -95, rssi_max: int = -30) -> None:
        """
        Map smoothed RSSI (-95 dBm to -30 dBm) to radius [0.08, 0.92].
        Stronger signal (-30 dBm) is closer to center (0.08), weaker is at perimeter (0.92).
        """
        clamped = max(rssi_min, min(rssi_max, self.smoothed_rssi))
        normalized = (clamped - rssi_min) / float(rssi_max - rssi_min) # 0.0 (weak) to 1.0 (strong)
        # Invert so 1.0 (strong) has small radius
        self.radar_distance_ratio = round(0.92 - (normalized * 0.84), 4)

    def update_rssi(self, new_rssi: int, alpha: float = 0.4) -> None:
        """Update telemetry with Exponential Moving Average (EMA)."""
        self.latest_rssi = new_rssi
        self.smoothed_rssi = (alpha * float(new_rssi)) + ((1.0 - alpha) * self.smoothed_rssi)
        if new_rssi < self.min_rssi:
            self.min_rssi = new_rssi
        if new_rssi > self.max_rssi:
            self.max_rssi = new_rssi
        self.update_radar_distance()

    def to_dict(self) -> dict[str, Any]:
        """Convert contact to serializable dictionary."""
        return {
            "contact_id": self.contact_id,
            "session_id": self.session_id,
            "normalized_identifier": self.normalized_identifier,
            "signal_type": self.signal_type,
            "mac_address": self.mac_address,
            "is_randomized": self.is_randomized,
            "ssid": self.ssid,
            "device_name": self.device_name,
            "state": self.state.value,
            "latest_rssi": self.latest_rssi,
            "smoothed_rssi": round(self.smoothed_rssi, 1),
            "min_rssi": self.min_rssi,
            "max_rssi": self.max_rssi,
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
            "classification_confidence": round(self.classification_confidence, 2),
            "classification_reason": self.classification_reason,
            "classification_evidence": self.classification_evidence,
            "priority": self.priority,
            "watchlist_matched": self.watchlist_matched,
            "watchlist_notes": self.watchlist_notes,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "observation_count": self.observation_count,
            "radar_angle_degrees": round(self.radar_angle_degrees, 1),
            "radar_distance_ratio": self.radar_distance_ratio,
        }
