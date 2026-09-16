"""
CSV export engine for contacts and observations.
"""

import csv
import io
from typing import Any
from application.models.contact import CorrelatedContact
from application.models.observation import NormalizedObservation


def export_contacts_to_csv(contacts: list[CorrelatedContact] | list[dict[str, Any]]) -> str:
    """Generate RFC 4180 CSV string of correlated contacts."""
    output = io.StringIO()
    fieldnames = [
        "contact_id",
        "signal_type",
        "mac_address",
        "is_randomized",
        "ssid",
        "device_name",
        "state",
        "latest_rssi",
        "smoothed_rssi",
        "min_rssi",
        "max_rssi",
        "rssi_category",
        "channel",
        "frequency",
        "band",
        "security",
        "manufacturer",
        "oui",
        "device_category",
        "classification_confidence",
        "priority",
        "watchlist_matched",
        "first_seen",
        "last_seen",
        "observation_count",
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()

    for c in contacts:
        data = c.to_dict() if hasattr(c, "to_dict") else dict(c)
        writer.writerow(data)

    return output.getvalue()


def export_observations_to_csv(observations: list[NormalizedObservation] | list[dict[str, Any]]) -> str:
    """Generate RFC 4180 CSV string of timestamped observations."""
    output = io.StringIO()
    fieldnames = [
        "observation_id",
        "session_id",
        "timestamp",
        "source",
        "interface",
        "mac_address",
        "rssi",
        "rssi_category",
        "channel",
        "frequency",
        "band",
        "ssid",
        "security",
        "manufacturer",
        "device_category",
        "priority",
        "watchlist_matched",
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()

    for obs in observations:
        data = obs.to_dict() if hasattr(obs, "to_dict") else dict(obs)
        writer.writerow(data)

    return output.getvalue()
