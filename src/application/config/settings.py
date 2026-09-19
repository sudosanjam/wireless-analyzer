"""
Central configuration settings loader.
"""

from pathlib import Path
from typing import Any
import yaml
from pydantic import BaseModel, Field


class ServerSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False


class ScannerSettings(BaseModel):
    wifi_enabled: bool = True
    ble_enabled: bool = True
    mock_mode: bool = False
    scan_interval_seconds: float = 2.0
    interface: str = "auto"
    wifi_backend: str = "auto"
    ble_backend: str = "auto"
    ble_interface: str = "auto"
    active_survey: bool = False


class TimeoutSettings(BaseModel):
    active_threshold_seconds: float = 6.0
    recent_threshold_seconds: float = 20.0
    stale_threshold_seconds: float = 60.0


class RSSIThresholdSettings(BaseModel):
    strong: int = -55
    medium: int = -75


class StorageSettings(BaseModel):
    database_path: str = "data/app.db"
    retention_days: int = 30
    auto_prune_on_startup: bool = True


class AlertSettings(BaseModel):
    audio_enabled: bool = False
    audio_volume: float = 0.5
    debounce_seconds: float = 5.0


class LoggingSettings(BaseModel):
    level: str = "INFO"
    format: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


class PathSettings(BaseModel):
    oui_database: str = "data/oui/oui.csv"
    signatures_file: str = "config/signatures.yaml"
    watchlist_file: str = "config/watchlist.yaml"


class AppConfig(BaseModel):
    server: ServerSettings = Field(default_factory=ServerSettings)
    scanners: ScannerSettings = Field(default_factory=ScannerSettings)
    timeouts: TimeoutSettings = Field(default_factory=TimeoutSettings)
    rssi_thresholds: RSSIThresholdSettings = Field(default_factory=RSSIThresholdSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    alerts: AlertSettings = Field(default_factory=AlertSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    paths: PathSettings = Field(default_factory=PathSettings)


def find_project_root() -> Path:
    """Find the root directory of the project."""
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").exists() or (parent / "config" / "default_config.yaml").exists():
            return parent
    return Path.cwd()


def load_config(
    config_path: str | Path | None = None,
    overrides: dict[str, Any] | None = None
) -> AppConfig:
    """
    Load configuration from yaml file, applying defaults and overrides.
    """
    root = find_project_root()
    default_yaml = root / "config" / "default_config.yaml"
    user_yaml = root / "config" / "config.yaml"
    
    config_data: dict[str, Any] = {}
    
    if default_yaml.exists():
        try:
            with open(default_yaml, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    config_data.update(loaded)
        except Exception:
            pass

    # Merge user-specific config if present
    if config_path:
        cp = Path(config_path)
        if cp.exists():
            with open(cp, "r", encoding="utf-8") as f:
                user_loaded = yaml.safe_load(f)
                if isinstance(user_loaded, dict):
                    _deep_merge(config_data, user_loaded)
    elif user_yaml.exists():
        try:
            with open(user_yaml, "r", encoding="utf-8") as f:
                user_loaded = yaml.safe_load(f)
                if isinstance(user_loaded, dict):
                    _deep_merge(config_data, user_loaded)
        except Exception:
            pass

    # Merge programmatic overrides
    if overrides:
        _deep_merge(config_data, overrides)

    # Normalize relative paths to project root
    if "paths" in config_data:
        for k, v in config_data["paths"].items():
            if isinstance(v, str) and not Path(v).is_absolute():
                config_data["paths"][k] = str(root / v)
                
    if "storage" in config_data and "database_path" in config_data["storage"]:
        db_p = config_data["storage"]["database_path"]
        if not Path(db_p).is_absolute():
            config_data["storage"]["database_path"] = str(root / db_p)

    return AppConfig.model_validate(config_data)


def _deep_merge(base: dict[str, Any], update: dict[str, Any]) -> None:
    for k, v in update.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
