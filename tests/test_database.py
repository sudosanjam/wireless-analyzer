"""
Unit tests for SQLite storage layer and repository operations.
"""

import time
from application.storage.repository import SignalRepository
from application.models.session import Session
from application.models.contact import CorrelatedContact, ContactState
from application.models.observation import NormalizedObservation
from application.models.event import EnvironmentalEvent


def test_session_lifecycle(repo: SignalRepository):
    sess = Session(
        session_id="test-session-abc",
        interface="wlan0",
        wifi_enabled=True,
        ble_enabled=True,
        scanner_backend="nmcli",
    )
    repo.create_session(sess)

    latest = repo.get_latest_session()
    assert latest is not None
    assert latest.session_id == "test-session-abc"
    assert latest.interface == "wlan0"
    assert latest.status == "RUNNING"

    # Update session
    sess.status = "COMPLETED"
    sess.end_time = time.time()
    sess.total_observations = 100
    sess.unique_contacts = 15
    repo.update_session(sess)

    updated = repo.get_session("test-session-abc")
    assert updated is not None
    assert updated.status == "COMPLETED"
    assert updated.total_observations == 100
    assert updated.unique_contacts == 15


def test_contacts_and_observations_persistence(repo: SignalRepository):
    sess = Session(session_id="session-persistence-1")
    repo.create_session(sess)

    contact = CorrelatedContact(
        normalized_identifier="00:11:22:33:44:55",
        signal_type="wifi",
        session_id="session-persistence-1",
        ssid="Test-Persistence-SSID",
        state=ContactState.ACTIVE,
        latest_rssi=-55,
        manufacturer="Cisco Systems",
        device_category="NETWORK_INFRASTRUCTURE",
    )
    repo.upsert_contacts([contact])

    saved_contacts = repo.get_session_contacts("session-persistence-1")
    assert len(saved_contacts) == 1
    assert saved_contacts[0]["mac_address"] == "00:11:22:33:44:55"
    assert saved_contacts[0]["ssid"] == "Test-Persistence-SSID"

    # Insert Observations Batch
    obs = NormalizedObservation(
        session_id="session-persistence-1",
        source="wifi",
        interface="wlan0",
        mac_address="00:11:22:33:44:55",
        is_randomized=False,
        rssi=-55,
        rssi_category="STRONG",
        ssid="Test-Persistence-SSID",
    )
    repo.insert_observations_batch([obs])

    saved_obs = repo.get_session_observations("session-persistence-1")
    assert len(saved_obs) == 1
    assert saved_obs[0]["mac_address"] == "00:11:22:33:44:55"


def test_events_persistence(repo: SignalRepository):
    sess = Session(session_id="session-event-1")
    repo.create_session(sess)

    event = EnvironmentalEvent(
        session_id="session-event-1",
        event_type="WATCHLIST_MATCH",
        severity="HIGH",
        mac_address="10:06:1C:11:22:33",
        message="Watchlist match on Flipper Zero",
    )
    repo.insert_event(event)

    saved_events = repo.get_session_events("session-event-1")
    assert len(saved_events) == 1
    assert saved_events[0]["event_type"] == "WATCHLIST_MATCH"
    assert saved_events[0]["severity"] == "HIGH"


def test_retention_pruning(repo: SignalRepository):
    # Old completed session (40 days ago)
    old_time = time.time() - (40 * 86400)
    old_sess = Session(session_id="old-session", start_time=old_time, status="COMPLETED")
    repo.create_session(old_sess)

    # Current running session
    cur_sess = Session(session_id="cur-session", status="RUNNING")
    repo.create_session(cur_sess)

    # Prune retention > 30 days
    pruned = repo.prune_retention(retention_days=30)
    assert pruned >= 1

    assert repo.get_session("old-session") is None
    assert repo.get_session("cur-session") is not None
