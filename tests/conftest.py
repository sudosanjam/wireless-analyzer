"""
Pytest fixtures and test environment setup.
"""

import os
from pathlib import Path
import pytest
from application.config.settings import load_config, AppConfig
from application.storage.database import DatabaseManager
from application.storage.repository import SignalRepository
from application.detection.oui import OUILookupEngine
from application.detection.signatures import SignatureRegistry
from application.detection.classifier import DeviceClassifier
from application.detection.watchlist import WatchlistEngine
from application.engine.normalizer import ObservationNormalizer


@pytest.fixture
def temp_db(tmp_path: Path) -> DatabaseManager:
    db_file = tmp_path / "test_app.db"
    return DatabaseManager(db_file)


@pytest.fixture
def repo(temp_db: DatabaseManager) -> SignalRepository:
    return SignalRepository(temp_db)


@pytest.fixture
def test_config() -> AppConfig:
    return load_config()


@pytest.fixture
def oui_engine(test_config: AppConfig) -> OUILookupEngine:
    return OUILookupEngine(test_config.paths.oui_database)


@pytest.fixture
def signatures(test_config: AppConfig) -> SignatureRegistry:
    return SignatureRegistry(test_config.paths.signatures_file)


@pytest.fixture
def watchlist(test_config: AppConfig) -> WatchlistEngine:
    return WatchlistEngine(test_config.paths.watchlist_file)


@pytest.fixture
def classifier(oui_engine: OUILookupEngine, signatures: SignatureRegistry) -> DeviceClassifier:
    return DeviceClassifier(oui_engine, signatures)


@pytest.fixture
def normalizer(oui_engine: OUILookupEngine, classifier: DeviceClassifier, watchlist: WatchlistEngine) -> ObservationNormalizer:
    return ObservationNormalizer(
        oui_engine=oui_engine,
        classifier=classifier,
        watchlist=watchlist,
    )
