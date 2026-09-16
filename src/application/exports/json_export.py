"""
Structured JSON export engine for observation sessions.
"""

import json
from typing import Any
from application.models.session import Session
from application.models.contact import CorrelatedContact
from application.models.observation import NormalizedObservation
from application.models.event import EnvironmentalEvent
from application.analytics.environment import EnvironmentalAnalyticsReport


def export_session_to_json(
    session: Session,
    contacts: list[CorrelatedContact] | list[dict[str, Any]],
    observations: list[NormalizedObservation] | list[dict[str, Any]] | None = None,
    events: list[EnvironmentalEvent] | list[dict[str, Any]] | None = None,
    analytics: EnvironmentalAnalyticsReport | None = None,
    indent: int = 2,
) -> str:
    """Generate structured JSON document containing full session telemetry."""
    contacts_data = [c.to_dict() if hasattr(c, "to_dict") else c for c in (contacts or [])]
    obs_data = [o.to_dict() if hasattr(o, "to_dict") else o for o in (observations or [])]
    events_data = [e.to_dict() if hasattr(e, "to_dict") else e for e in (events or [])]

    payload = {
        "schema_version": "1.0.0",
        "session": session.to_dict() if hasattr(session, "to_dict") else dict(session),
        "analytics": analytics.to_dict() if analytics else None,
        "contacts_count": len(contacts_data),
        "contacts": contacts_data,
        "events_count": len(events_data),
        "events": events_data,
        "observations_count": len(obs_data),
        "observations": obs_data,
    }

    return json.dumps(payload, indent=indent, default=str)
