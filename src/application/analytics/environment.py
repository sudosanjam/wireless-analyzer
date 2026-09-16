"""
Environmental analytics and spectrum statistical distribution calculations.
"""

from dataclasses import dataclass, field
import math
from typing import Any
from application.models.contact import CorrelatedContact, ContactState


@dataclass
class EnvironmentalAnalyticsReport:
    total_contacts: int = 0
    active_contacts: int = 0
    new_contacts: int = 0
    recent_contacts: int = 0
    stale_contacts: int = 0
    wifi_contacts: int = 0
    ble_contacts: int = 0
    randomized_mac_count: int = 0
    
    # RSSI telemetry
    min_rssi: int = -95
    max_rssi: int = -30
    mean_rssi: float = -90.0
    rssi_distribution: dict[str, int] = field(default_factory=dict) # {"STRONG": N, "MEDIUM": N, "WEAK": N}
    
    # Channel and Spectrum telemetry
    channel_distribution: dict[int, int] = field(default_factory=dict)
    band_distribution: dict[str, int] = field(default_factory=dict)
    
    # Manufacturer breakdown
    manufacturer_distribution: dict[str, int] = field(default_factory=dict)
    
    # Category breakdown
    category_distribution: dict[str, int] = field(default_factory=dict)
    
    # Watchlist count
    watchlist_match_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_contacts": self.total_contacts,
            "active_contacts": self.active_contacts,
            "new_contacts": self.new_contacts,
            "recent_contacts": self.recent_contacts,
            "stale_contacts": self.stale_contacts,
            "wifi_contacts": self.wifi_contacts,
            "ble_contacts": self.ble_contacts,
            "randomized_mac_count": self.randomized_mac_count,
            "rssi_stats": {
                "min": self.min_rssi,
                "max": self.max_rssi,
                "mean": round(self.mean_rssi, 1),
                "distribution": self.rssi_distribution,
            },
            "channel_distribution": self.channel_distribution,
            "band_distribution": self.band_distribution,
            "manufacturer_distribution": self.manufacturer_distribution,
            "category_distribution": self.category_distribution,
            "watchlist_match_count": self.watchlist_match_count,
        }


class EnvironmentalAnalyticsEngine:
    """Computes real-time environmental metrics across active and historical contacts."""

    @staticmethod
    def analyze(contacts: list[CorrelatedContact] | list[dict[str, Any]]) -> EnvironmentalAnalyticsReport:
        if not contacts:
            return EnvironmentalAnalyticsReport(
                rssi_distribution={"STRONG": 0, "MEDIUM": 0, "WEAK": 0}
            )

        report = EnvironmentalAnalyticsReport()
        report.total_contacts = len(contacts)

        rssi_values: list[int] = []
        rssi_dist = {"STRONG": 0, "MEDIUM": 0, "WEAK": 0}
        chan_dist: dict[int, int] = {}
        band_dist: dict[str, int] = {}
        man_dist: dict[str, int] = {}
        cat_dist: dict[str, int] = {}

        for c in contacts:
            state_val = getattr(c, "state", None)
            if state_val is not None and hasattr(state_val, "value"):
                state_str = state_val.value
            else:
                state_str = getattr(c, "state", None) or (c.get("state") if isinstance(c, dict) else "ACTIVE")

            sig_type = getattr(c, "signal_type", None) or (c.get("signal_type") if isinstance(c, dict) else "wifi")
            is_rand = getattr(c, "is_randomized", None) if not isinstance(c, dict) else bool(c.get("is_randomized"))
            watch_match = getattr(c, "watchlist_matched", None) if not isinstance(c, dict) else bool(c.get("watchlist_matched"))
            rssi = getattr(c, "latest_rssi", None) if not isinstance(c, dict) else c.get("latest_rssi", -90)
            rssi_cat = getattr(c, "rssi_category", None) or (c.get("rssi_category") if isinstance(c, dict) else "WEAK")
            chan = getattr(c, "channel", None) if not isinstance(c, dict) else c.get("channel")
            band = getattr(c, "band", None) or (c.get("band") if isinstance(c, dict) else "Unknown Band")
            mfg = getattr(c, "manufacturer", None) or (c.get("manufacturer") if isinstance(c, dict) else "Unknown")
            cat = getattr(c, "device_category", None) or (c.get("device_category") if isinstance(c, dict) else "UNKNOWN")

            # States
            if state_str == "NEW":
                report.new_contacts += 1
                report.active_contacts += 1
            elif state_str == "ACTIVE":
                report.active_contacts += 1
            elif state_str == "RECENT":
                report.recent_contacts += 1
            elif state_str == "STALE":
                report.stale_contacts += 1

            # Types
            if sig_type == "wifi":
                report.wifi_contacts += 1
            elif sig_type == "ble":
                report.ble_contacts += 1

            if is_rand:
                report.randomized_mac_count += 1

            if watch_match:
                report.watchlist_match_count += 1

            # RSSI
            if rssi is not None:
                rssi_values.append(int(rssi))
            rssi_dist[rssi_cat] = rssi_dist.get(rssi_cat, 0) + 1

            # Channel
            if chan is not None:
                chan_dist[int(chan)] = chan_dist.get(int(chan), 0) + 1

            # Band
            band_dist[band] = band_dist.get(band, 0) + 1

            # Manufacturer
            man_dist[mfg] = man_dist.get(mfg, 0) + 1

            # Category
            cat_dist[cat] = cat_dist.get(cat, 0) + 1

        if rssi_values:
            report.min_rssi = min(rssi_values)
            report.max_rssi = max(rssi_values)
            report.mean_rssi = sum(rssi_values) / len(rssi_values)

        report.rssi_distribution = rssi_dist
        report.channel_distribution = dict(sorted(chan_dist.items(), key=lambda x: x[0]))
        report.band_distribution = dict(sorted(band_dist.items(), key=lambda x: x[1], reverse=True))
        report.manufacturer_distribution = dict(sorted(man_dist.items(), key=lambda x: x[1], reverse=True)[:15])
        report.category_distribution = dict(sorted(cat_dist.items(), key=lambda x: x[1], reverse=True))

        return report
