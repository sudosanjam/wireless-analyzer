"""
Environmental Change Detector.
Analyzes statistical deltas in wireless density, spectrum usage, and turnover.
"""

from dataclasses import dataclass
import time
from typing import Any
from application.models.contact import CorrelatedContact, ContactState
from application.models.event import EnvironmentalEvent


@dataclass
class EnvironmentalSnapshot:
    timestamp: float
    total_contacts: int
    active_contacts: int
    wifi_count: int
    ble_count: int
    top_channels: dict[int, int]
    avg_rssi: float


class EnvironmentalChangeDetector:
    """Detects and quantifies macro-environmental changes between scan epochs."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self._last_snapshot: EnvironmentalSnapshot | None = None

    def evaluate_deltas(self, contacts: list[CorrelatedContact]) -> list[EnvironmentalEvent]:
        """
        Compare current contact state with previous snapshot to detect notable changes.
        """
        now = time.time()
        active = [c for c in contacts if c.state in (ContactState.NEW, ContactState.ACTIVE)]
        wifi = [c for c in contacts if c.signal_type == "wifi"]
        ble = [c for c in contacts if c.signal_type == "ble"]
        
        # Calculate channel usage
        channel_counts: dict[int, int] = {}
        for c in contacts:
            if c.channel is not None:
                channel_counts[c.channel] = channel_counts.get(c.channel, 0) + 1

        avg_rssi = sum(c.latest_rssi for c in contacts) / len(contacts) if contacts else -90.0

        current_snap = EnvironmentalSnapshot(
            timestamp=now,
            total_contacts=len(contacts),
            active_contacts=len(active),
            wifi_count=len(wifi),
            ble_count=len(ble),
            top_channels=channel_counts,
            avg_rssi=avg_rssi,
        )

        events: list[EnvironmentalEvent] = []

        if self._last_snapshot is not None:
            # Check for significant delta in active observations
            diff_active = current_snap.active_contacts - self._last_snapshot.active_contacts
            if abs(diff_active) >= 5:
                sign_str = f"+{diff_active}" if diff_active > 0 else str(diff_active)
                events.append(
                    EnvironmentalEvent(
                        session_id=self.session_id,
                        event_type="DENSITY_DELTA",
                        severity="LOW",
                        label="Observation Density Shift",
                        message=f"{sign_str} active wireless contacts compared to previous measurement interval",
                        details={
                            "previous_active": self._last_snapshot.active_contacts,
                            "current_active": current_snap.active_contacts,
                            "delta": diff_active,
                        },
                    )
                )

        self._last_snapshot = current_snap
        return events
