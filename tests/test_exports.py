"""
Unit tests for CSV, JSON, and Markdown Debrief export engines.
"""

import json
from application.models.session import Session
from application.models.contact import CorrelatedContact, ContactState
from application.models.observation import NormalizedObservation
from application.exports import (
    export_contacts_to_csv,
    export_observations_to_csv,
    export_session_to_json,
    generate_markdown_debrief,
)


def test_csv_export():
    contact = CorrelatedContact(
        normalized_identifier="00:11:22:33:44:55",
        signal_type="wifi",
        session_id="sess-export-1",
        ssid="Test-Export-SSID",
        state=ContactState.ACTIVE,
        latest_rssi=-52,
        channel=36,
        manufacturer="Cisco Systems",
        device_category="NETWORK_INFRASTRUCTURE",
    )
    csv_str = export_contacts_to_csv([contact])
    assert "contact_id,signal_type,mac_address" in csv_str
    assert "00:11:22:33:44:55" in csv_str
    assert "Test-Export-SSID" in csv_str
    assert "Cisco Systems" in csv_str


def test_json_export():
    sess = Session(session_id="sess-json-1", interface="wlan0", scanner_backend="mock")
    contact = CorrelatedContact(
        normalized_identifier="00:11:22:33:44:55",
        signal_type="wifi",
        session_id="sess-json-1",
        ssid="Test-JSON-SSID",
        state=ContactState.ACTIVE,
        latest_rssi=-52,
    )
    json_str = export_session_to_json(sess, [contact])
    data = json.loads(json_str)

    assert data["schema_version"] == "1.0.0"
    assert data["session"]["session_id"] == "sess-json-1"
    assert data["contacts_count"] == 1
    assert data["contacts"][0]["mac_address"] == "00:11:22:33:44:55"


def test_markdown_debrief_generation():
    sess = Session(
        session_id="sess-debrief-1",
        interface="wlan0",
        scanner_backend="mock",
        status="COMPLETED",
    )
    c1 = CorrelatedContact(
        normalized_identifier="00:11:22:33:44:55",
        signal_type="wifi",
        session_id="sess-debrief-1",
        ssid="Enterprise-AP",
        state=ContactState.ACTIVE,
        latest_rssi=-48,
        channel=36,
        manufacturer="Cisco Systems",
        device_category="NETWORK_INFRASTRUCTURE",
        classification_confidence=0.85,
    )
    c2 = CorrelatedContact(
        normalized_identifier="10:06:1C:AA:BB:CC",
        signal_type="ble",
        session_id="sess-debrief-1",
        device_name="Flipper Zero",
        state=ContactState.ACTIVE,
        latest_rssi=-65,
        manufacturer="Flipper Devices",
        device_category="COMMERCIAL_HARDWARE",
        watchlist_matched=True,
        watchlist_notes=["Watchlist: Flipper Zero / Multi-tool"],
    )

    md = generate_markdown_debrief(sess, [c1, c2])

    # Assert required sections exist
    assert "# ENVIRONMENTAL SIGNAL OBSERVATION DEBRIEF" in md
    assert "## 1. SESSION PROFILE" in md
    assert "## 2. EXECUTIVE SUMMARY" in md
    assert "## 3. SIGNAL STRENGTH DISTRIBUTION" in md
    assert "## 4. FREQUENCY SPECTRUM & CHANNELS" in md
    assert "## 5. HARDWARE & VENDOR CENSUS" in md
    assert "## 6. HEURISTIC CLASSIFICATION BREAKDOWN" in md
    assert "## 7. NOTABLE OBSERVATIONS & WATCHLIST ALERTS" in md
    assert "## 8. DETAILED CONTACT INVENTORY" in md
    assert "## 9. METHODOLOGY & OBSERVATION BOUNDARY" in md
    assert "## 10. TECHNICAL LIMITATIONS" in md

    # Assert content rendering
    assert "Cisco Systems" in md
    assert "Flipper Zero" in md
    assert "Enterprise-AP" in md
    assert "RSSI Is Not Physical Distance" in md
