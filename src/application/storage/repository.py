"""
Data repository operations for sessions, contacts, observations, and events.
"""

import json
import time
from typing import Any
from application.models.session import Session
from application.models.contact import CorrelatedContact, ContactState
from application.models.observation import NormalizedObservation
from application.models.event import EnvironmentalEvent
from application.storage.database import DatabaseManager
from application.utils.logging import get_logger

logger = get_logger("repository")


class SignalRepository:
    """Repository handling all CRUD and batch operations on SQLite."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    # ------------------ Session Management ------------------
    def create_session(self, session: Session) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO sessions (
                    id, start_time, end_time, interface, wifi_enabled,
                    ble_enabled, scanner_backend, status, total_observations,
                    unique_contacts, config_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.session_id,
                    session.start_time,
                    session.end_time,
                    session.interface,
                    1 if session.wifi_enabled else 0,
                    1 if session.ble_enabled else 0,
                    session.scanner_backend,
                    session.status,
                    session.total_observations,
                    session.unique_contacts,
                    json.dumps(session.config_snapshot),
                ),
            )

    def update_session(self, session: Session) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                """
                UPDATE sessions SET
                    end_time = ?,
                    status = ?,
                    total_observations = ?,
                    unique_contacts = ?
                WHERE id = ?
                """,
                (
                    session.end_time,
                    session.status,
                    session.total_observations,
                    session.unique_contacts,
                    session.session_id,
                ),
            )

    def get_latest_session(self) -> Session | None:
        with self.db.transaction() as conn:
            row = conn.execute(
                "SELECT * FROM sessions ORDER BY start_time DESC LIMIT 1"
            ).fetchone()
            if not row:
                return None
            return self._row_to_session(row)

    def get_session(self, session_id: str) -> Session | None:
        with self.db.transaction() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_session(row)

    def list_sessions(self, limit: int = 50) -> list[Session]:
        with self.db.transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM sessions ORDER BY start_time DESC LIMIT ?", (limit,)
            ).fetchall()
            return [self._row_to_session(r) for r in rows]

    def _row_to_session(self, row: Any) -> Session:
        config = {}
        if row["config_json"]:
            try:
                config = json.loads(row["config_json"])
            except Exception:
                pass
        return Session(
            session_id=row["id"],
            start_time=row["start_time"],
            end_time=row["end_time"],
            interface=row["interface"],
            wifi_enabled=bool(row["wifi_enabled"]),
            ble_enabled=bool(row["ble_enabled"]),
            scanner_backend=row["scanner_backend"],
            status=row["status"],
            total_observations=row["total_observations"] or 0,
            unique_contacts=row["unique_contacts"] or 0,
            config_snapshot=config,
        )

    # ------------------ Contacts Operations ------------------
    def upsert_contacts(self, contacts: list[CorrelatedContact]) -> None:
        if not contacts:
            return
        
        with self.db.transaction() as conn:
            for c in contacts:
                conn.execute(
                    """
                    INSERT INTO contacts (
                        id, session_id, normalized_identifier, signal_type,
                        mac_address, is_randomized, ssid, device_name, state,
                        latest_rssi, smoothed_rssi, min_rssi, max_rssi,
                        rssi_category, channel, frequency, band, security,
                        manufacturer, oui, device_category, classification_confidence,
                        classification_reason, priority, watchlist_matched,
                        first_seen, last_seen, observation_count,
                        radar_angle_degrees, radar_distance_ratio
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    ON CONFLICT(id) DO UPDATE SET
                        state = excluded.state,
                        latest_rssi = excluded.latest_rssi,
                        smoothed_rssi = excluded.smoothed_rssi,
                        min_rssi = excluded.min_rssi,
                        max_rssi = excluded.max_rssi,
                        rssi_category = excluded.rssi_category,
                        channel = excluded.channel,
                        frequency = excluded.frequency,
                        band = excluded.band,
                        security = excluded.security,
                        ssid = COALESCE(excluded.ssid, contacts.ssid),
                        device_name = COALESCE(excluded.device_name, contacts.device_name),
                        manufacturer = excluded.manufacturer,
                        device_category = excluded.device_category,
                        classification_confidence = excluded.classification_confidence,
                        priority = excluded.priority,
                        watchlist_matched = excluded.watchlist_matched,
                        last_seen = excluded.last_seen,
                        observation_count = excluded.observation_count,
                        radar_distance_ratio = excluded.radar_distance_ratio
                    """,
                    (
                        c.contact_id,
                        c.session_id,
                        c.normalized_identifier,
                        c.signal_type,
                        c.mac_address,
                        1 if c.is_randomized else 0,
                        c.ssid,
                        c.device_name,
                        c.state.value,
                        c.latest_rssi,
                        c.smoothed_rssi,
                        c.min_rssi,
                        c.max_rssi,
                        c.rssi_category,
                        c.channel,
                        c.frequency,
                        c.band,
                        c.security,
                        c.manufacturer,
                        c.oui,
                        c.device_category,
                        c.classification_confidence,
                        c.classification_reason,
                        c.priority,
                        1 if c.watchlist_matched else 0,
                        c.first_seen,
                        c.last_seen,
                        c.observation_count,
                        c.radar_angle_degrees,
                        c.radar_distance_ratio,
                    ),
                )

    def get_session_contacts(self, session_id: str) -> list[dict[str, Any]]:
        with self.db.transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM contacts WHERE session_id = ? ORDER BY last_seen DESC",
                (session_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    # ------------------ Observations Operations ------------------
    def insert_observations_batch(self, observations: list[NormalizedObservation]) -> None:
        if not observations:
            return
        
        with self.db.transaction() as conn:
            conn.executemany(
                """
                INSERT INTO observations (
                    id, session_id, contact_id, timestamp, source, interface,
                    mac_address, rssi, rssi_category, channel, frequency,
                    ssid, security, manufacturer, device_category, raw_metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        obs.observation_id,
                        obs.session_id,
                        obs.mac_address,
                        obs.timestamp,
                        obs.source,
                        obs.interface,
                        obs.mac_address,
                        obs.rssi,
                        obs.rssi_category,
                        obs.channel,
                        obs.frequency,
                        obs.ssid,
                        obs.security,
                        obs.manufacturer,
                        obs.device_category,
                        json.dumps(obs.raw_metadata),
                    )
                    for obs in observations
                ],
            )

    def get_session_observations(self, session_id: str, limit: int = 1000) -> list[dict[str, Any]]:
        with self.db.transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM observations WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    # ------------------ Events Operations ------------------
    def insert_event(self, event: EnvironmentalEvent) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO events (
                    id, session_id, timestamp, event_type, severity,
                    contact_id, mac_address, label, message, details_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.session_id,
                    event.timestamp,
                    event.event_type,
                    event.severity,
                    event.contact_id,
                    event.mac_address,
                    event.label,
                    event.message,
                    json.dumps(event.details),
                ),
            )

    def get_session_events(self, session_id: str, limit: int = 200) -> list[dict[str, Any]]:
        with self.db.transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM events WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    # ------------------ Retention Pruning ------------------
    def prune_retention(self, retention_days: int = 30) -> int:
        cutoff = time.time() - (retention_days * 86400)
        with self.db.transaction() as conn:
            # Delete old sessions (cascades to contacts, observations, events)
            cur = conn.execute(
                "DELETE FROM sessions WHERE start_time < ? AND status != 'RUNNING'",
                (cutoff,),
            )
            deleted = cur.rowcount
            if deleted > 0:
                logger.info("Pruned %d historical sessions older than %d days", deleted, retention_days)
            return deleted
