"""
FastAPI application server with integrated observation engine background worker.
"""

import asyncio
from pathlib import Path
from typing import Callable
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from application.config.settings import AppConfig, find_project_root
from application.models.session import Session
from application.models.event import EnvironmentalEvent
from application.engine.normalizer import ObservationNormalizer
from application.engine.contact_tracker import ContactTracker
from application.engine.change_detector import EnvironmentalChangeDetector
from application.detection.oui import OUILookupEngine
from application.detection.signatures import SignatureRegistry
from application.detection.classifier import DeviceClassifier
from application.detection.watchlist import WatchlistEngine
from application.analytics.environment import EnvironmentalAnalyticsEngine
from application.storage.database import DatabaseManager
from application.storage.repository import SignalRepository
from application.scanners.base import BaseScannerBackend
from application.scanners.mock_scanner import MockScannerBackend
from application.scanners.wifi_nmcli import NMCLIBackend
from application.scanners.wifi_iw import IWBackend
from application.scanners.wifi_raw import ScapyRawBackend
from application.scanners.ble_bleak import BleakScannerBackend
from application.scanners.ble_bluez import BlueZBackend
from application.web.ws import WebSocketManager
from application.web.routes import create_routes
from application.utils.logging import get_logger

from contextlib import asynccontextmanager

logger = get_logger("web.server")


class SignalObserverServer:
    """Integrated observation platform web server and coordinator."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.root_dir = find_project_root()
        
        # Database & Repository
        db_path = Path(config.storage.database_path)
        self.db = DatabaseManager(db_path)
        self.repo = SignalRepository(self.db)
        
        # Auto prune old data if configured
        if config.storage.auto_prune_on_startup:
            self.repo.prune_retention(config.storage.retention_days)

        # Detection Subsystems
        self.oui_engine = OUILookupEngine(config.paths.oui_database)
        self.signatures = SignatureRegistry(config.paths.signatures_file)
        self.watchlist = WatchlistEngine(config.paths.watchlist_file)
        self.classifier = DeviceClassifier(self.oui_engine, self.signatures)
        
        # Normalization
        self.normalizer = ObservationNormalizer(
            oui_engine=self.oui_engine,
            classifier=self.classifier,
            watchlist=self.watchlist,
            strong_rssi=config.rssi_thresholds.strong,
            medium_rssi=config.rssi_thresholds.medium,
        )

        # Session Lifecycle
        backend_name = "mock" if config.scanners.mock_mode else config.scanners.wifi_backend
        self.current_session = Session(
            interface=config.scanners.interface,
            wifi_enabled=config.scanners.wifi_enabled,
            ble_enabled=config.scanners.ble_enabled,
            scanner_backend=backend_name,
            config_snapshot=config.model_dump(),
        )
        self.repo.create_session(self.current_session)

        # Contact Tracking & Environmental Change Detection
        self.ws_manager = WebSocketManager()
        self.tracker = ContactTracker(
            session_id=self.current_session.session_id,
            active_threshold=config.timeouts.active_threshold_seconds,
            recent_threshold=config.timeouts.recent_threshold_seconds,
            stale_threshold=config.timeouts.stale_threshold_seconds,
            on_event_callback=self._handle_event,
        )
        self.change_detector = EnvironmentalChangeDetector(self.current_session.session_id)

        # Scanner Backends
        self.scanners: list[BaseScannerBackend] = []
        self._init_scanners()

        self._scan_task: asyncio.Task | None = None
        self._is_running = False

        # Web App setup with lifespan
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            self.start_background_scanner()
            yield
            self.stop_background_scanner()

        self.app = FastAPI(title="Signal Observer", version="0.1.0", lifespan=lifespan)
        self._setup_app()

    def _init_scanners(self) -> None:
        """Initialize active scanner backends according to configuration."""
        if self.config.scanners.mock_mode:
            logger.info("Engaging realistic MockScannerBackend")
            self.scanners.append(MockScannerBackend(interface="mock-0"))
            return

        # Wi-Fi Backends
        if self.config.scanners.wifi_enabled:
            backend_pref = self.config.scanners.wifi_backend.lower()
            iface = self.config.scanners.interface

            if backend_pref == "nmcli" or (backend_pref == "auto" and NMCLIBackend().is_available()):
                self.scanners.append(NMCLIBackend(interface=iface, config={"active_survey": self.config.scanners.active_survey}))
            elif backend_pref == "iw" or (backend_pref == "auto" and IWBackend(iface).is_available()):
                self.scanners.append(IWBackend(interface=iface))
            elif backend_pref == "raw":
                self.scanners.append(ScapyRawBackend(interface=iface))
            else:
                logger.info("No physical Wi-Fi scanner backend available, falling back to mock scanner")
                self.scanners.append(MockScannerBackend(interface="mock-0"))

        # BLE Backends
        if self.config.scanners.ble_enabled:
            ble_pref = self.config.scanners.ble_backend.lower()
            if ble_pref == "bleak" or (ble_pref == "auto" and BleakScannerBackend().is_available()):
                self.scanners.append(BleakScannerBackend())
            elif ble_pref == "bluez" or (ble_pref == "auto" and BlueZBackend().is_available()):
                self.scanners.append(BlueZBackend())

    def _setup_app(self) -> None:
        static_dir = Path(__file__).parent / "static"
        templates_dir = Path(__file__).parent / "templates"
        
        templates = Jinja2Templates(directory=str(templates_dir))
        self.app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        # REST Routes
        rest_router = create_routes(
            templates=templates,
            tracker_getter=lambda: self.tracker,
            repo=self.repo,
            session_getter=lambda: self.current_session,
        )
        self.app.include_router(rest_router)

        # WebSocket Route
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await self.ws_manager.connect(websocket)
            # Send initial full state sync
            contacts = self.tracker.get_all_contacts()
            analytics = EnvironmentalAnalyticsEngine.analyze(contacts)
            await websocket.send_json({
                "type": "FULL_STATE",
                "session": self.current_session.to_dict(),
                "contacts": [c.to_dict() for c in contacts],
                "analytics": analytics.to_dict(),
            })
            try:
                while True:
                    await websocket.receive_text()
            except WebSocketDisconnect:
                self.ws_manager.disconnect(websocket)
            except Exception:
                self.ws_manager.disconnect(websocket)

    def _handle_event(self, event: EnvironmentalEvent) -> None:
        """Called when contact tracker or change detector fires an event."""
        self.repo.insert_event(event)
        # Broadcast event over WebSocket
        asyncio.create_task(self.ws_manager.broadcast({
            "type": "NEW_EVENT",
            "event": event.to_dict(),
        }))

    def start_background_scanner(self) -> None:
        self._is_running = True
        for s in self.scanners:
            s.start()
        self._scan_task = asyncio.create_task(self._scan_loop())
        logger.info("Background scanner task started with interval %.1fs", self.config.scanners.scan_interval_seconds)

    def stop_background_scanner(self) -> None:
        self._is_running = False
        if self._scan_task:
            self._scan_task.cancel()
        for s in self.scanners:
            s.stop()
        
        # Finalize Session in Database
        self.current_session.status = "COMPLETED"
        self.current_session.end_time = asyncio.get_event_loop().time()
        self.repo.update_session(self.current_session)
        logger.info("Background scanner stopped and session archived.")

    async def _scan_loop(self) -> None:
        interval = max(0.5, self.config.scanners.scan_interval_seconds)
        while self._is_running:
            try:
                # 1. Run Scanners (offloaded to thread executor to avoid blocking async loop)
                raw_obs = []
                for scanner in self.scanners:
                    obs_batch = await asyncio.to_thread(scanner.scan)
                    raw_obs.extend(obs_batch)

                # 2. Normalize and Ingest
                normalized_batch = []
                for raw in raw_obs:
                    norm = self.normalizer.normalize(raw, session_id=self.current_session.session_id)
                    if norm:
                        normalized_batch.append(norm)
                        self.tracker.process_observation(norm)

                # 3. Update Temporal States
                self.tracker.update_temporal_states()

                # 4. Detect Environmental Macro Changes
                current_contacts = self.tracker.get_all_contacts()
                delta_events = self.change_detector.evaluate_deltas(current_contacts)
                for ev in delta_events:
                    self._handle_event(ev)

                # 5. Database Batch Persistence
                if normalized_batch:
                    self.repo.insert_observations_batch(normalized_batch)
                self.repo.upsert_contacts(current_contacts)

                # Update session metrics
                self.current_session.total_observations += len(normalized_batch)
                self.current_session.unique_contacts = len(current_contacts)

                # 6. Broadcast Telemetry Delta to Connected Web Clients
                analytics = EnvironmentalAnalyticsEngine.analyze(current_contacts)
                await self.ws_manager.broadcast({
                    "type": "STATE_DELTA",
                    "session": self.current_session.to_dict(),
                    "contacts": [c.to_dict() for c in current_contacts],
                    "analytics": analytics.to_dict(),
                })

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in observation loop: %s", e, exc_info=True)

            await asyncio.sleep(interval)
