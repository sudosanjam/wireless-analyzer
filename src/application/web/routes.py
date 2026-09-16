"""
FastAPI REST API routes and template endpoints.
"""

from pathlib import Path
from typing import Any
from fastapi import APIRouter, Request, HTTPException, Response
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

from application.models.session import Session
from application.engine.contact_tracker import ContactTracker
from application.analytics.environment import EnvironmentalAnalyticsEngine
from application.storage.repository import SignalRepository
from application.scanners.diagnostics import run_diagnostics, format_diagnostics_table
from application.exports import (
    export_contacts_to_csv,
    export_session_to_json,
    generate_markdown_debrief,
)

router = APIRouter()


def create_routes(
    templates: Jinja2Templates,
    tracker_getter: Any,
    repo: SignalRepository,
    session_getter: Any,
) -> APIRouter:
    
    @router.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return templates.TemplateResponse(request=request, name="index.html")

    @router.get("/api/session")
    async def get_session():
        session = session_getter()
        if not session:
            raise HTTPException(status_code=404, detail="No active session")
        return session.to_dict()

    @router.get("/api/contacts")
    async def get_contacts():
        tracker: ContactTracker = tracker_getter()
        contacts = tracker.get_all_contacts()
        return [c.to_dict() for c in contacts]

    @router.get("/api/analytics")
    async def get_analytics():
        tracker: ContactTracker = tracker_getter()
        contacts = tracker.get_all_contacts()
        report = EnvironmentalAnalyticsEngine.analyze(contacts)
        return report.to_dict()

    @router.get("/api/events")
    async def get_events(limit: int = 100):
        session: Session = session_getter()
        if not session:
            return []
        return repo.get_session_events(session.session_id, limit=limit)

    @router.get("/api/diagnostics")
    async def get_diagnostics():
        diag_items = run_diagnostics()
        table_str = format_diagnostics_table(diag_items)
        return {
            "items": [
                {
                    "category": d.category,
                    "name": d.name,
                    "status": d.status,
                    "details": d.details,
                }
                for d in diag_items
            ],
            "table": table_str,
        }

    @router.get("/api/export/{fmt}")
    async def export_data(fmt: str):
        session: Session = session_getter()
        if not session:
            raise HTTPException(status_code=404, detail="No active session")
        
        tracker: ContactTracker = tracker_getter()
        contacts = tracker.get_all_contacts()
        events = repo.get_session_events(session.session_id, limit=500)
        analytics = EnvironmentalAnalyticsEngine.analyze(contacts)

        fmt_lower = fmt.lower()
        if fmt_lower == "csv":
            csv_str = export_contacts_to_csv(contacts)
            return Response(
                content=csv_str,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=session_{session.session_id[:8]}_contacts.csv"},
            )
        elif fmt_lower == "json":
            json_str = export_session_to_json(session, contacts, events=events, analytics=analytics)
            return Response(
                content=json_str,
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename=session_{session.session_id[:8]}.json"},
            )
        elif fmt_lower in ("debrief", "md", "markdown"):
            md_str = generate_markdown_debrief(session, contacts, events=events, analytics=analytics)
            return Response(
                content=md_str,
                media_type="text/markdown",
                headers={"Content-Disposition": f"attachment; filename=session_{session.session_id[:8]}_debrief.md"},
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format '{fmt}'. Use 'csv', 'json', or 'debrief'")

    return router
