"""
Unit tests for Contact Tracking, State Transitions, and Correlation.
"""

import time
from application.engine.contact_tracker import ContactTracker
from application.models.contact import ContactState
from application.models.observation import NormalizedObservation
from application.models.event import EnvironmentalEvent


def test_contact_tracker_lifecycle():
    events: list[EnvironmentalEvent] = []
    
    tracker = ContactTracker(
        session_id="test-session-1",
        active_threshold=2.0,
        recent_threshold=5.0,
        stale_threshold=10.0,
        on_event_callback=lambda ev: events.append(ev),
    )

    t0 = 1000.0
    obs1 = NormalizedObservation(
        session_id="test-session-1",
        timestamp=t0,
        source="wifi",
        interface="wlan0",
        mac_address="00:11:22:33:44:55",
        is_randomized=False,
        ssid="Test-AP",
        rssi=-50,
        rssi_category="STRONG",
    )

    # 1. First observation -> NEW state & event
    contact = tracker.process_observation(obs1)
    assert contact.state == ContactState.NEW
    assert contact.observation_count == 1
    assert contact.latest_rssi == -50
    assert contact.smoothed_rssi == -50.0
    assert len(events) == 1
    assert events[0].event_type == "NEW_CONTACT"

    # 2. Second observation at t0 + 1s -> ACTIVE state & smoothed RSSI
    obs2 = NormalizedObservation(
        session_id="test-session-1",
        timestamp=t0 + 1.0,
        source="wifi",
        interface="wlan0",
        mac_address="00:11:22:33:44:55",
        is_randomized=False,
        ssid="Test-AP",
        rssi=-60,
        rssi_category="MEDIUM",
    )
    contact2 = tracker.process_observation(obs2)
    assert contact2.state == ContactState.ACTIVE
    assert contact2.observation_count == 2
    assert contact2.latest_rssi == -60
    # EMA: (0.4 * -60) + (0.6 * -50) = -24 + -30 = -54.0
    assert round(contact2.smoothed_rssi, 1) == -54.0

    # 3. Advance time to t0 + 4s (beyond active_threshold 2.0s, within recent_threshold 5.0s)
    tracker.update_temporal_states(current_time=t0 + 4.0)
    assert contact.state == ContactState.RECENT

    # 4. Advance time to t0 + 12s (beyond stale_threshold 10.0s)
    tracker.update_temporal_states(current_time=t0 + 12.0)
    assert contact.state == ContactState.STALE
    assert any(e.event_type == "CONTACT_DEPARTED" for e in events)


def test_deterministic_radar_angle():
    obs = NormalizedObservation(
        session_id="sess",
        source="wifi",
        interface="wlan0",
        mac_address="00:11:22:33:44:55",
        is_randomized=False,
        rssi=-50,
        rssi_category="STRONG",
    )
    tracker = ContactTracker(session_id="sess")
    c1 = tracker.process_observation(obs)
    angle1 = c1.radar_angle_degrees

    # Create another tracker with identical MAC -> angle must be identical (deterministic)
    tracker2 = ContactTracker(session_id="sess2")
    c2 = tracker2.process_observation(obs)
    angle2 = c2.radar_angle_degrees

    assert angle1 == angle2
    assert 0.0 <= angle1 < 360.0
