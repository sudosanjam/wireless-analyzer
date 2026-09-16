"""
Correlated Contact Tracker.
Manages temporal state transitions (NEW -> ACTIVE -> RECENT -> STALE),
signal smoothing, and session contact lifecycle.
"""

import time
from typing import Callable
from application.models.observation import NormalizedObservation
from application.models.contact import CorrelatedContact, ContactState
from application.models.event import EnvironmentalEvent
from application.utils.logging import get_logger

logger = get_logger("contact_tracker")


class ContactTracker:
    """
    Maintains the in-memory pool of active and historical session contacts.
    Performs deterministic contact correlation, state transitions, and change event triggering.
    """

    def __init__(
        self,
        session_id: str,
        active_threshold: float = 6.0,
        recent_threshold: float = 20.0,
        stale_threshold: float = 60.0,
        on_event_callback: Callable[[EnvironmentalEvent], None] | None = None,
    ) -> None:
        self.session_id = session_id
        self.active_threshold = active_threshold
        self.recent_threshold = recent_threshold
        self.stale_threshold = stale_threshold
        self.on_event_callback = on_event_callback
        
        # In-memory contact table keyed by normalized_identifier
        self._contacts: dict[str, CorrelatedContact] = {}

    def get_all_contacts(self) -> list[CorrelatedContact]:
        """Return snapshot of all tracked session contacts."""
        return list(self._contacts.values())

    def get_contact(self, identifier: str) -> CorrelatedContact | None:
        return self._contacts.get(identifier)

    def process_observation(self, obs: NormalizedObservation) -> CorrelatedContact:
        """
        Incorporate a normalized observation into the contact pool.
        Updates signal telemetry, state, and triggers NEW/WATCHLIST events if applicable.
        """
        ident = obs.mac_address
        existing = self._contacts.get(ident)

        if existing is None:
            # First time seen in this session -> NEW contact
            contact = CorrelatedContact(
                normalized_identifier=ident,
                signal_type=obs.source,
                session_id=self.session_id,
                mac_address=obs.mac_address,
                is_randomized=obs.is_randomized,
                ssid=obs.ssid,
                device_name=obs.device_name,
                state=ContactState.NEW,
                latest_rssi=obs.rssi,
                rssi_category=obs.rssi_category,
                channel=obs.channel,
                frequency=obs.frequency,
                band=obs.band,
                security=obs.security,
                capabilities=obs.capabilities,
                service_uuids=obs.service_uuids,
                manufacturer=obs.manufacturer,
                oui=obs.oui,
                device_category=obs.device_category,
                classification_confidence=obs.classification_confidence,
                classification_reason=obs.classification_reason,
                classification_evidence=obs.classification_evidence,
                priority=obs.priority,
                watchlist_matched=obs.watchlist_matched,
                watchlist_notes=obs.watchlist_notes,
                first_seen=obs.timestamp,
                last_seen=obs.timestamp,
                observation_count=1,
            )
            self._contacts[ident] = contact

            # Trigger NEW_CONTACT event
            self._dispatch_event(
                event_type="NEW_CONTACT",
                severity=obs.priority,
                contact_id=contact.contact_id,
                mac_address=obs.mac_address,
                label=f"New {obs.source.upper()} Contact Observed",
                message=f"Observed {obs.source.upper()} device {obs.mac_address} ({obs.ssid or obs.device_name or obs.manufacturer})",
                details=contact.to_dict(),
            )

            # Trigger WATCHLIST_MATCH if flagged
            if obs.watchlist_matched:
                self._dispatch_event(
                    event_type="WATCHLIST_MATCH",
                    severity="HIGH",
                    contact_id=contact.contact_id,
                    mac_address=obs.mac_address,
                    label="Watchlist Match Detected",
                    message=f"Matched watchlist item: {', '.join(obs.watchlist_notes)}",
                    details=contact.to_dict(),
                )

            return contact

        else:
            # Update existing contact
            existing.observation_count += 1
            existing.last_seen = obs.timestamp
            existing.state = ContactState.ACTIVE
            existing.update_rssi(obs.rssi)
            existing.rssi_category = obs.rssi_category
            
            # Enrich metadata if previously missing
            if obs.ssid and not existing.ssid:
                existing.ssid = obs.ssid
            if obs.device_name and not existing.device_name:
                existing.device_name = obs.device_name
            if obs.channel is not None:
                existing.channel = obs.channel
            if obs.frequency is not None:
                existing.frequency = obs.frequency
            if obs.band is not None:
                existing.band = obs.band
            if obs.security and not existing.security:
                existing.security = obs.security
            if obs.capabilities:
                existing.capabilities = list(set(existing.capabilities + obs.capabilities))
            if obs.service_uuids:
                existing.service_uuids = list(set(existing.service_uuids + obs.service_uuids))

            return existing

    def update_temporal_states(self, current_time: float | None = None) -> list[CorrelatedContact]:
        """
        Evaluate time since last observation for all contacts and transition states:
        - If last_seen within active_threshold -> ACTIVE
        - If last_seen within recent_threshold -> RECENT
        - If last_seen beyond stale_threshold -> STALE
        """
        now = current_time if current_time is not None else time.time()
        changed: list[CorrelatedContact] = []

        for contact in self._contacts.values():
            elapsed = now - contact.last_seen
            old_state = contact.state

            if elapsed <= self.active_threshold:
                new_state = ContactState.ACTIVE if old_state != ContactState.NEW else ContactState.NEW
            elif elapsed <= self.recent_threshold:
                new_state = ContactState.RECENT
            else:
                new_state = ContactState.STALE

            if new_state != old_state:
                contact.state = new_state
                contact.last_state_change = now
                changed.append(contact)

                if new_state == ContactState.STALE and old_state != ContactState.STALE:
                    self._dispatch_event(
                        event_type="CONTACT_DEPARTED",
                        severity="INFO",
                        contact_id=contact.contact_id,
                        mac_address=contact.mac_address,
                        label="Contact Stale / Departed",
                        message=f"Contact {contact.mac_address} has not been observed for {int(elapsed)}s",
                        details={"elapsed_seconds": elapsed, "last_rssi": contact.latest_rssi},
                    )

        return changed

    def _dispatch_event(
        self,
        event_type: str,
        severity: str,
        contact_id: str | None,
        mac_address: str | None,
        label: str,
        message: str,
        details: dict,
    ) -> None:
        event = EnvironmentalEvent(
            session_id=self.session_id,
            event_type=event_type,
            severity=severity,
            contact_id=contact_id,
            mac_address=mac_address,
            label=label,
            message=message,
            details=details,
        )
        if self.on_event_callback:
            try:
                self.on_event_callback(event)
            except Exception as e:
                logger.error("Error in on_event callback: %s", e)
