"""
Environmental Debrief generator.
Produces structured, professional Markdown debrief reports suitable for operator review or LLM analysis.
"""

from datetime import datetime, timezone
from typing import Any
from application.models.session import Session
from application.models.contact import CorrelatedContact
from application.analytics.environment import EnvironmentalAnalyticsReport, EnvironmentalAnalyticsEngine


def generate_markdown_debrief(
    session: Session,
    contacts: list[CorrelatedContact] | list[dict[str, Any]],
    events: list[dict[str, Any]] | None = None,
    analytics: EnvironmentalAnalyticsReport | None = None,
) -> str:
    """Generate comprehensive Markdown environmental debrief report."""
    # Convert contacts if raw dicts
    contact_objs: list[CorrelatedContact] = []
    contact_dicts: list[dict[str, Any]] = []

    for c in contacts:
        if isinstance(c, CorrelatedContact):
            contact_objs.append(c)
            contact_dicts.append(c.to_dict())
        else:
            contact_dicts.append(c)

    if analytics is None:
        analytics = EnvironmentalAnalyticsEngine.analyze(contacts)

    start_iso = datetime.fromtimestamp(session.start_time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    end_iso = (
        datetime.fromtimestamp(session.end_time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        if session.end_time
        else "In Progress / Active"
    )

    lines: list[str] = []

    # Header
    lines.append("# ENVIRONMENTAL SIGNAL OBSERVATION DEBRIEF")
    lines.append(f"**Session ID:** `{session.session_id}`  ")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  ")
    lines.append(f"**Platform Target:** Kali Linux Reference Target / Offline Observer")
    lines.append("\n---\n")

    # 1. Session Metadata
    lines.append("## 1. SESSION PROFILE")
    lines.append(f"- **Start Time:** {start_iso}")
    lines.append(f"- **End Time:** {end_iso}")
    lines.append(f"- **Duration:** {session.duration_seconds:.1f} seconds")
    lines.append(f"- **Primary Interface:** `{session.interface}`")
    lines.append(f"- **Scanner Backend:** `{session.scanner_backend}`")
    lines.append(f"- **Wi-Fi Observation:** {'Enabled' if session.wifi_enabled else 'Disabled'}")
    lines.append(f"- **BLE Observation:** {'Enabled' if session.ble_enabled else 'Disabled'}")
    lines.append(f"- **Completion Status:** `{session.status}`")
    lines.append("")

    # 2. Executive Summary
    lines.append("## 2. EXECUTIVE SUMMARY")
    lines.append(f"During this observation session, a total of **{analytics.total_contacts} unique wireless contacts** were correlated:")
    lines.append(f"- **Active Contacts:** {analytics.active_contacts}")
    lines.append(f"- **Wi-Fi Infrastructure / APs:** {analytics.wifi_contacts}")
    lines.append(f"- **Bluetooth Low Energy (BLE) Entities:** {analytics.ble_contacts}")
    lines.append(f"- **Randomized MAC Identifiers:** {analytics.randomized_mac_count} ({_pct(analytics.randomized_mac_count, analytics.total_contacts)} of total)")
    lines.append(f"- **Watchlist Hits:** {analytics.watchlist_match_count}")
    lines.append("")

    # 3. Signal & RSSI Distribution
    lines.append("## 3. SIGNAL STRENGTH DISTRIBUTION")
    lines.append(f"- **Peak RSSI:** {analytics.max_rssi} dBm")
    lines.append(f"- **Minimum RSSI:** {analytics.min_rssi} dBm")
    lines.append(f"- **Mean RSSI:** {analytics.mean_rssi:.1f} dBm")
    lines.append("")
    lines.append("| Category | Threshold | Contact Count | Percentage |")
    lines.append("|---|---|---|---|")
    for cat in ["STRONG", "MEDIUM", "WEAK"]:
        cnt = analytics.rssi_distribution.get(cat, 0)
        thresh_desc = ">= -55 dBm" if cat == "STRONG" else ("-55 to -75 dBm" if cat == "MEDIUM" else "< -75 dBm")
        lines.append(f"| **{cat}** | `{thresh_desc}` | {cnt} | {_pct(cnt, analytics.total_contacts)} |")
    lines.append("")

    # 4. Spectrum & Channel Distribution
    lines.append("## 4. FREQUENCY SPECTRUM & CHANNELS")
    if analytics.band_distribution:
        lines.append("### Frequency Bands")
        for band, count in analytics.band_distribution.items():
            lines.append(f"- **{band}:** {count} contacts ({_pct(count, analytics.total_contacts)})")
        lines.append("")

    if analytics.channel_distribution:
        lines.append("### Wi-Fi Channel Density")
        lines.append("| Channel | Frequency | Active Contacts | Density |")
        lines.append("|---|---|---|---|")
        for chan, count in analytics.channel_distribution.items():
            lines.append(f"| Ch {chan} | {_chan_freq(chan)} | {count} | {_pct(count, analytics.total_contacts)} |")
        lines.append("")

    # 5. Manufacturer Census
    lines.append("## 5. HARDWARE & VENDOR CENSUS")
    if analytics.manufacturer_distribution:
        lines.append("| Manufacturer / Organization | Contacts | Share |")
        lines.append("|---|---|---|")
        for mfg, count in analytics.manufacturer_distribution.items():
            lines.append(f"| **{mfg}** | {count} | {_pct(count, analytics.total_contacts)} |")
    else:
        lines.append("*No manufacturer records identified in session.*")
    lines.append("")

    # 6. Classification Breakdown
    lines.append("## 6. HEURISTIC CLASSIFICATION BREAKDOWN")
    if analytics.category_distribution:
        lines.append("| Device Category | Contacts | Percentage |")
        lines.append("|---|---|---|")
        for cat, count in analytics.category_distribution.items():
            lines.append(f"| `{cat}` | {count} | {_pct(count, analytics.total_contacts)} |")
    lines.append("")

    # 7. Notable Observations & Watchlist Matches
    lines.append("## 7. NOTABLE OBSERVATIONS & WATCHLIST ALERTS")
    watchlist_contacts = [c for c in contact_dicts if c.get("watchlist_matched")]
    if watchlist_contacts:
        lines.append(f"**{len(watchlist_contacts)} contacts matched configured watchlist rules:**")
        lines.append("")
        lines.append("| Type | Identifier | Name / SSID | Manufacturer | Watchlist Notes |")
        lines.append("|---|---|---|---|---|")
        for wc in watchlist_contacts:
            id_val = wc.get("mac_address", "N/A")
            name_val = wc.get("ssid") or wc.get("device_name") or "*(Hidden/Unadvertised)*"
            mfg_val = wc.get("manufacturer", "Unknown")
            notes_val = ", ".join(wc.get("watchlist_notes", [])) or "Match"
            lines.append(f"| {wc.get('signal_type', '').upper()} | `{id_val}` | **{name_val}** | {mfg_val} | `{notes_val}` |")
        lines.append("")
    else:
        lines.append("*No watchlist matches triggered during this session.*")
        lines.append("")

    # 8. Contact Inventory Table
    lines.append("## 8. DETAILED CONTACT INVENTORY (TOP 30)")
    sorted_contacts = sorted(contact_dicts, key=lambda x: x.get("latest_rssi", -100), reverse=True)[:30]
    lines.append("| State | Type | Identifier | SSID / Name | RSSI | Ch | Manufacturer | Category | Conf |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for c in sorted_contacts:
        st = c.get("state", "N/A")
        sig = c.get("signal_type", "wifi")[:3].upper()
        mac = c.get("mac_address", "N/A")
        label = c.get("ssid") or c.get("device_name") or "*(Hidden)*"
        rssi = f"{c.get('latest_rssi', -90)} dBm"
        ch = str(c.get("channel")) if c.get("channel") is not None else "-"
        mfg = (c.get("manufacturer") or "Unknown")[:18]
        cat = (c.get("device_category") or "UNKNOWN")
        conf = f"{int(c.get('classification_confidence', 0.0) * 100)}%"
        lines.append(f"| `{st}` | {sig} | `{mac}` | {label} | `{rssi}` | {ch} | {mfg} | `{cat}` | {conf} |")
    lines.append("")

    # 9. Methodology
    lines.append("## 9. METHODOLOGY & OBSERVATION BOUNDARY")
    lines.append("This report was compiled strictly through **passive reception of broadcast wireless telemetry** exposed to local system interfaces. "
                 "The platform does **not** engage in active probing, packet injection, authentication attacks, deauthentication, "
                 "credential harvesting, or connection establishment. All data points reflect observable broadcast metadata.")
    lines.append("")

    # 10. Explicit Limitations
    lines.append("## 10. TECHNICAL LIMITATIONS & NON-PRECISION NOTICE")
    lines.append("1. **RSSI Is Not Physical Distance:** Received Signal Strength Indicator (RSSI) is influenced by physical obstructions, multipath reflections, and antenna orientation. It is an environmental RF indicator, not a calibrated distance measurement.")
    lines.append("2. **Radar Position Is Not Radio Direction Finding (RDF):** Visual radar positioning utilizes a deterministic hash for display clustering. It does not represent directional bearing or geographic coordinates.")
    lines.append("3. **Randomized MAC Identifiers:** Modern mobile operating systems utilize MAC address randomization for probe scanning. Devices with Locally Administered addresses cannot be persistently tracked across non-continuous observation windows.")
    lines.append("4. **Heuristic Classification:** Device categories and confidence scores are rule-based inferences and should not be treated as absolute hardware certifications.")
    lines.append("")

    return "\n".join(lines)


def _pct(part: int, total: int) -> str:
    if not total:
        return "0.0%"
    return f"{(part / total) * 100:.1f}%"


def _chan_freq(chan: int) -> str:
    if 1 <= chan <= 14:
        return "2.4 GHz"
    elif 32 <= chan <= 177:
        return "5 GHz"
    elif 180 <= chan <= 233:
        return "6 GHz"
    return "Spectrum"
