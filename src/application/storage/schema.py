"""
SQLite schema definitions and DDL migrations.
"""

SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

-- Sessions Table
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    start_time REAL NOT NULL,
    end_time REAL,
    interface TEXT NOT NULL,
    wifi_enabled INTEGER NOT NULL DEFAULT 1,
    ble_enabled INTEGER NOT NULL DEFAULT 1,
    scanner_backend TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'RUNNING',
    total_observations INTEGER DEFAULT 0,
    unique_contacts INTEGER DEFAULT 0,
    config_json TEXT
);

-- Correlated Contacts Table
CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    normalized_identifier TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    mac_address TEXT NOT NULL,
    is_randomized INTEGER NOT NULL DEFAULT 0,
    ssid TEXT,
    device_name TEXT,
    state TEXT NOT NULL,
    latest_rssi INTEGER NOT NULL,
    smoothed_rssi REAL NOT NULL,
    min_rssi INTEGER NOT NULL,
    max_rssi INTEGER NOT NULL,
    rssi_category TEXT NOT NULL,
    channel INTEGER,
    frequency INTEGER,
    band TEXT,
    security TEXT,
    manufacturer TEXT NOT NULL DEFAULT 'Unknown',
    oui TEXT,
    device_category TEXT NOT NULL DEFAULT 'UNKNOWN',
    classification_confidence REAL DEFAULT 0.0,
    classification_reason TEXT,
    priority TEXT NOT NULL DEFAULT 'INFO',
    watchlist_matched INTEGER NOT NULL DEFAULT 0,
    first_seen REAL NOT NULL,
    last_seen REAL NOT NULL,
    observation_count INTEGER NOT NULL DEFAULT 1,
    radar_angle_degrees REAL DEFAULT 0.0,
    radar_distance_ratio REAL DEFAULT 0.5,
    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Raw Observations Table (Historical Log)
CREATE TABLE IF NOT EXISTS observations (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    contact_id TEXT,
    timestamp REAL NOT NULL,
    source TEXT NOT NULL,
    interface TEXT NOT NULL,
    mac_address TEXT NOT NULL,
    rssi INTEGER NOT NULL,
    rssi_category TEXT NOT NULL,
    channel INTEGER,
    frequency INTEGER,
    ssid TEXT,
    security TEXT,
    manufacturer TEXT,
    device_category TEXT,
    raw_metadata_json TEXT,
    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Environmental and Watchlist Events Table
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    timestamp REAL NOT NULL,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'INFO',
    contact_id TEXT,
    mac_address TEXT,
    label TEXT,
    message TEXT NOT NULL,
    details_json TEXT,
    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Indexes for Fast Query & Analytics
CREATE INDEX IF NOT EXISTS idx_contacts_session ON contacts(session_id);
CREATE INDEX IF NOT EXISTS idx_contacts_mac ON contacts(mac_address);
CREATE INDEX IF NOT EXISTS idx_contacts_last_seen ON contacts(last_seen);
CREATE INDEX IF NOT EXISTS idx_contacts_manufacturer ON contacts(manufacturer);
CREATE INDEX IF NOT EXISTS idx_contacts_category ON contacts(device_category);

CREATE INDEX IF NOT EXISTS idx_observations_session ON observations(session_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_observations_mac ON observations(mac_address);
CREATE INDEX IF NOT EXISTS idx_observations_channel ON observations(channel);

CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_events_severity ON events(severity);
"""
