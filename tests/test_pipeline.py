"""
End-to-end full pipeline integration test.
Acquisition -> Normalization -> Classification -> Tracking -> Storage -> Analytics -> Export
"""

from application.scanners.mock_scanner import MockScannerBackend
from application.models.session import Session
from application.engine.normalizer import ObservationNormalizer
from application.engine.contact_tracker import ContactTracker
from application.engine.change_detector import EnvironmentalChangeDetector
from application.analytics.environment import EnvironmentalAnalyticsEngine
from application.storage.repository import SignalRepository
from application.exports import generate_markdown_debrief, export_session_to_json, export_contacts_to_csv


def test_full_pipeline_integration(normalizer: ObservationNormalizer, repo: SignalRepository):
    # 1. Initialize Session
    session = Session(
        session_id="pipeline-session-test",
        interface="mock-0",
        scanner_backend="mock",
    )
    repo.create_session(session)

    # 2. Initialize Tracker & Change Detector
    events_captured = []
    tracker = ContactTracker(
        session_id=session.session_id,
        on_event_callback=lambda ev: events_captured.append(ev),
    )
    change_detector = EnvironmentalChangeDetector(session_id=session.session_id)

    # 3. Acquire from Mock Scanner
    scanner = MockScannerBackend(interface="mock-0")
    scanner.start()
    raw_batch = scanner.scan()
    assert len(raw_batch) > 0

    # 4. Normalize & Ingest into Tracker
    normalized_batch = []
    for raw in raw_batch:
        norm = normalizer.normalize(raw, session_id=session.session_id)
        if norm:
            normalized_batch.append(norm)
            tracker.process_observation(norm)

    assert len(normalized_batch) > 0

    # 5. Advance states and detect changes
    tracker.update_temporal_states()
    current_contacts = tracker.get_all_contacts()
    delta_events = change_detector.evaluate_deltas(current_contacts)
    for ev in delta_events:
        events_captured.append(ev)

    # 6. Database Batch Persistence
    repo.insert_observations_batch(normalized_batch)
    repo.upsert_contacts(current_contacts)
    for ev in events_captured:
        repo.insert_event(ev)

    session.status = "COMPLETED"
    session.total_observations = len(normalized_batch)
    session.unique_contacts = len(current_contacts)
    repo.update_session(session)

    # 7. Analytics Calculation
    analytics = EnvironmentalAnalyticsEngine.analyze(current_contacts)
    assert analytics.total_contacts == len(current_contacts)
    assert analytics.active_contacts > 0
    assert len(analytics.rssi_distribution) == 3

    # 8. Exports Generation
    csv_out = export_contacts_to_csv(current_contacts)
    assert len(csv_out) > 0

    json_out = export_session_to_json(session, current_contacts, normalized_batch, events_captured, analytics)
    assert "schema_version" in json_out

    debrief_out = generate_markdown_debrief(session, current_contacts, [e.to_dict() for e in events_captured], analytics)
    assert "ENVIRONMENTAL SIGNAL OBSERVATION DEBRIEF" in debrief_out
    assert "## 1. SESSION PROFILE" in debrief_out

    # 9. Verify Database Records
    db_contacts = repo.get_session_contacts(session.session_id)
    db_obs = repo.get_session_observations(session.session_id)
    db_events = repo.get_session_events(session.session_id)

    assert len(db_contacts) == len(current_contacts)
    assert len(db_obs) == len(normalized_batch)
    assert len(db_events) == len(events_captured)

    scanner.stop()
