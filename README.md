# Signal Observer

### Kali Linux-First Passive Wireless Signal Observation & Environmental Analysis Platform

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Platform: Kali Linux](https://img.shields.io/badge/Platform-Kali%20Linux%20%7C%20Debian%20%7C%20Ubuntu-red.svg)](https://www.kali.org/)
[![Offline First](https://img.shields.io/badge/Offline-100%25%20Local-success.svg)](#offline-first-operation)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## ⚡ QUICK START

```bash
git clone <repository>
cd Analyzer
./install.sh
./run.sh
```

Then open the dashboard URL displayed in the terminal:
👉 **`http://127.0.0.1:8000`**

To launch in simulated demonstration / test mode without physical wireless adapters:
```bash
./run.sh --mock
```

---

## TABLE OF CONTENTS

1. [Overview](#1-overview)
2. [Core Capabilities](#2-core-capabilities)
3. [Passive Observation Model](#3-passive-observation-model)
4. [What the Platform Observes](#4-what-the-platform-observes)
5. [What the Platform Does NOT Do](#5-what-the-platform-does-not-do)
6. [Supported Platforms](#6-supported-platforms)
7. [Hardware Considerations](#7-hardware-considerations)
8. [Quick Start](#8-quick-start)
9. [Installation](#9-installation)
10. [Configuration](#10-configuration)
11. [Wi-Fi Observation Strategy](#11-wi-fi-observation-strategy)
12. [BLE Observation Strategy](#12-ble-observation-strategy)
13. [Dashboard Interface](#13-dashboard-interface)
14. [Radar Interpretation & Methodology](#14-radar-interpretation--methodology)
15. [OUI / Vendor Database](#15-oui--vendor-database)
16. [Classification Engine](#16-classification-engine)
17. [Watchlists & Alerts](#17-watchlists--alerts)
18. [Environmental Analytics](#18-environmental-analytics)
19. [Data Exports](#19-data-exports)
20. [Mock Simulation Mode](#20-mock-simulation-mode)
21. [First-Run Diagnostics](#21-first-run-diagnostics)
22. [Troubleshooting](#22-troubleshooting)
23. [Privacy Architecture](#23-privacy-architecture)
24. [Security Architecture](#24-security-architecture)
25. [Known Limitations](#25-known-limitations)
26. [Development & Contributing](#26-development--contributing)
27. [Automated Testing](#27-automated-testing)
28. [Deployment & Optional Systemd Service](#28-deployment--optional-systemd-service)
29. [Roadmap](#29-roadmap)
30. [License](#30-license)

---

## 1. Overview

**Signal Observer** is an open-source, locally-hosted, offline-capable passive wireless signal observation and environmental telemetry platform designed primarily for **Kali Linux**, Debian, and Ubuntu environments.

The platform transforms raw, broadcast RF metadata exposed to local system interfaces into structured, actionable environmental intelligence without actively communicating with, disrupting, or probing remote devices.

### Fundamental Workflow:
$$\text{Observe} \longrightarrow \text{Normalize} \longrightarrow \text{Correlate} \longrightarrow \text{Classify} \longrightarrow \text{Visualize} \longrightarrow \text{Analyze} \longrightarrow \text{Export}$$

---

## 2. Core Capabilities

- **Live Wi-Fi Observation**: Non-disruptive 802.11 AP metadata collection via `nmcli` and `iw` survey dumps.
- **Optional BLE Observation**: Passive Bluetooth Low Energy (BLE) advertisement scanning via `Bleak` and `BlueZ`.
- **Temporal State Tracking**: Automatic contact state transitions (`NEW` $\rightarrow$ `ACTIVE` $\rightarrow$ `RECENT` $\rightarrow$ `STALE`).
- **Signal Strength Smoothing**: Exponential Moving Average (EMA) smoothing of RSSI values.
- **Local OUI Identification**: Bundled local IEEE MAC prefix database (MA-L, MA-M, MA-S) operating 100% offline.
- **Evidence-Based Classification**: Transparent heuristic device categorization with confidence scoring and evidence tracking.
- **Tactical HTML5 Canvas Radar**: RSSI-mapped signal scope with rotating sweep and interactive blip tooltips.
- **Environmental Change Detection**: Detection of micro and macro shifts in wireless density, contact turnover, and RF spectrum usage.
- **Watchlist Engine**: Real-time alerts for targeted MAC prefixes, SSIDs, and vendor signatures.
- **Multi-Format Exports**: Tabular CSV, machine-readable structured JSON, and comprehensive Markdown Debriefs designed for direct LLM ingestion.
- **Least Privilege**: Operates entirely as an unprivileged user without requiring root.

---

## 3. Passive Observation Model

Signal Observer maintains strict adherence to passive monitoring boundaries:
- It only captures metadata **broadcast or locally exposed** to the host system.
- It does **not** transmit probe requests into unmanaged channels unless active survey is explicitly enabled.
- It does **not** authenticate, associate, pair, or establish transport-layer connections to observed devices.

---

## 4. What the Platform Observes

| Spectrum | Fields Collected |
|---|---|
| **Wi-Fi (802.11)** | BSSID, SSID, RSSI (dBm), Channel, Frequency (MHz), Band (2.4/5/6 GHz), Security Suite, Capabilities (ESS, HT, VHT, HE, WPS), OUI Vendor. |
| **BLE (Bluetooth LE)** | MAC Address, Advertised Name, RSSI (dBm), Service UUIDs, Manufacturer Data Company ID, Locally Administered (Randomized) bit. |

---

## 5. What the Platform Does NOT Do

To maintain safety, legality, and stability in production environments, the platform explicitly excludes:
- ❌ Deauthentication or disassociation attacks
- ❌ Packet injection or frame modification
- ❌ Credential harvesting or Evil-Twin AP deployment
- ❌ WPA/WPA2/WPA3 handshake cracking or traffic decryption
- ❌ Man-in-the-Middle (MITM) interception
- ❌ Bluetooth pairing, bonding, or GATT descriptor read/write
- ❌ Intrusive network port scanning or active device exploitation

---

## 6. Supported Platforms

- **Primary Reference**: **Kali Linux** (Rolling / Debian 12 base)
- **Secondary Reference**: Ubuntu 22.04 / 24.04 LTS, Debian 12 (Bookworm)
- **ARM SBCs**: Raspberry Pi 4 / 5 (Kali ARM, Raspberry Pi OS 64-bit)
- **Development Fallback**: macOS and Windows supported via native Python runner and high-fidelity Mock Mode.

---

## 7. Hardware Considerations

- **Wi-Fi Adapters**:
  - Integrated Intel Wi-Fi (`iwlwifi`), Realtek, Qualcomm, MediaTek.
  - USB Wi-Fi dongles (Alfa Network AWUS036ACH, Panda Wireless PAU09, TP-Link WN722N).
- **Bluetooth Adapters**:
  - Integrated Intel / Broadcom Bluetooth HCI adapters (`hci0`).
  - Standard USB Bluetooth 4.0 / 5.0+ dongles supported by BlueZ.

---

## 8. Quick Start

Run the automated installer and start observing:
```bash
git clone https://github.com/example/signal-observer.git
cd signal-observer
./install.sh
./run.sh
```

---

## 9. Installation

### Requirements:
- Python 3.11 or higher
- Linux utilities (optional, auto-detected): `network-manager` (`nmcli`), `iw`, `bluez` (`bluetoothctl`), `sqlite3`.

### On Kali Linux / Debian / Ubuntu:
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip network-manager iw bluez sqlite3
./install.sh
```

`install.sh` creates a dedicated virtual environment in `.venv`, installs packages safely, verifies system tools, and prepares local databases without modifying system-wide packages.

---

## 10. Configuration

Configuration is managed centrally in `config/default_config.yaml` or user overrides in `config/config.yaml`:

```yaml
server:
  host: "127.0.0.1"
  port: 8000
  debug: false

scanners:
  wifi_enabled: true
  ble_enabled: true
  mock_mode: false
  scan_interval_seconds: 2.0
  interface: "auto"
  wifi_backend: "auto"     # "auto", "nmcli", "iw", "raw", "mock"
  ble_backend: "auto"      # "auto", "bleak", "bluez", "mock"

timeouts:
  active_threshold_seconds: 6.0
  recent_threshold_seconds: 20.0
  stale_threshold_seconds: 60.0

rssi_thresholds:
  strong: -55
  medium: -75

storage:
  database_path: "data/app.db"
  retention_days: 30

alerts:
  audio_enabled: false     # Web Audio alert tones
```

---

## 11. Wi-Fi Observation Strategy

The system evaluates available Wi-Fi backends in priority order:
1. **`NMCLIBackend`**: Utilizes NetworkManager's cached wireless scan list. Non-disruptive, does not drop active network connections, and requires zero root privileges.
2. **`IWBackend`**: Queries `iw dev <iface> scan dump` to parse the kernel nl80211 survey tables.
3. **`ScapyRawBackend`**: Optional passive frame sniffer when an adapter is configured in monitor mode.
4. **`MockScannerBackend`**: Engaged when no physical Wi-Fi hardware is present.

---

## 12. BLE Observation Strategy

BLE observation runs asynchronously and independently of Wi-Fi:
- Uses `Bleak` or `BlueZ` to listen for advertising broadcasts.
- Parses advertising flags, complete/short local names, service UUIDs, and manufacturer company IDs.
- If Bluetooth hardware is unavailable or disabled, Wi-Fi observation continues uninterrupted.

---

## 13. Dashboard Interface

The local web interface (`http://127.0.0.1:8000`) features:
- **Telemetry Ribbon**: Live session ID, uptime, active/new contact counters, spectrum ratio, and alert counts.
- **Tactical Canvas Radar**: Signal strength scope plotting contacts with smooth blips, glowing halos, and real-time hover cards.
- **Live Contact Matrix**: Filterable, searchable, sortable table with RSSI signal meters, vendor badges, and category tags.
- **Spectrum Analytics**: RSSI histograms, channel density charts, and manufacturer breakdown charts.
- **Environmental Events Log**: Timestamped feed of new contacts, departures, and watchlist hits.
- **System Diagnostics Terminal**: Live inspection of local Python, tools, adapters, and databases.

---

## 14. Radar Interpretation & Methodology

> [!IMPORTANT]
> **Signal Strength Scope Notice:**
> The radar is an **RSSI signal-strength mapping**, NOT a radio direction finder (RDF).
> - **Radius ($r$):** Directly derived from normalized RSSI. Strong signals appear near the center (-30 dBm); weak signals appear near the perimeter (-95 dBm).
> - **Angle ($\theta$):** Derived deterministically from a SHA-256 hash of the device identifier. This clusters the same device consistently while distributing different devices evenly across 360 degrees.
> - **State Opacity:** `ACTIVE` (100% opacity), `RECENT` (55% opacity), `STALE` (20% opacity).

---

## 15. OUI / Vendor Database

- Includes an indexed local copy of the IEEE OUI registry (`data/oui/oui.csv`) containing over 45,000 assignments.
- Operates **100% offline**.
- Differentiates Universally Administered Addresses from Locally Administered (Randomized) Addresses.
- Offline update utility available via: `python -m application oui update`.

---

## 16. Classification Engine

Classification rules are defined in `config/signatures.yaml`. The engine evaluates:
- IEEE OUI Organization Name
- Broadcast SSID patterns (e.g. `DIRECT-.*HP`, `SmartLife_.*`, `Amazon-.*`)
- Advertised device names (e.g. `WH-1000XM4`, `Apple Watch`)
- BLE Service UUIDs (Audio, Exposure Notification, Fast Pair)
- 802.11 capability sets

Each classification generates an evidence list, heuristic confidence score ($0.0 \dots 1.0$), and category tag (`NETWORK_INFRASTRUCTURE`, `ROUTER_GATEWAY`, `MOBILE_DEVICE`, `IOT_EMBEDDED`, `AUDIO_PERIPHERAL`, `COMMERCIAL_HARDWARE`, `CONSUMER_ELECTRONICS`, or `UNKNOWN`).

---

## 17. Watchlists & Alerts

Configure sensitive patterns in `config/watchlist.yaml`:
```yaml
watchlist:
  - match_type: "SSID_REGEX"
    pattern: "(?i)(corp-secure|internal-wifi|surveillance)"
    label: "Sensitive SSID Pattern"
    priority: "HIGH"

  - match_type: "MANUFACTURER"
    pattern: "Flipper Devices"
    label: "Flipper Zero / Multi-tool"
    priority: "HIGH"
```
When a contact matches:
1. High-visibility red glowing halo appears on the radar.
2. An event is logged in the environmental feed.
3. Web Audio alert tone sounds (if audio is toggled on in the UI).

---

## 18. Environmental Analytics

Real-time statistical calculations include:
- **Signal Density**: Observations per second and active contacts per epoch.
- **Spectrum Allocation**: 2.4 GHz vs. 5 GHz vs. 6 GHz vs. BLE channel distributions.
- **RSSI Dispersion**: Minimum, maximum, mean, and standard deviation across Strong/Medium/Weak bins.
- **Hardware Census**: Top identified vendors vs. randomized MAC ratios.

---

## 19. Data Exports

Export session data via the Web Dashboard or CLI:

```bash
# Markdown Environmental Debrief (Ready for LLM consumption)
python -m application export --format debrief --session latest -o debrief.md

# Tabular CSV
python -m application export --format csv --session latest -o contacts.csv

# Structured JSON
python -m application export --format json --session latest -o session.json
```

---

## 20. Mock Simulation Mode

Run with realistic simulated multi-vendor RF telemetry without physical hardware:
```bash
./run.sh --mock
```
Simulates enterprise Cisco APs, Ubiquiti gateways, TP-Link routers, Espressif IoT nodes, Apple mobile devices with randomized MACs, Sony BLE audio devices, and intermittent watchlist targets.

---

## 21. First-Run Diagnostics

Inspect host environment capabilities from the CLI:
```bash
python -m application diag
```
Output:
```text
═══════════════════════════════════════════════════════════════════════════
         SIGNAL OBSERVER — PRE-FLIGHT SYSTEM DIAGNOSTICS                   
═══════════════════════════════════════════════════════════════════════════

[Runtime]
  [✓] AVAILABLE   Python Version           : Python 3.13.15
  [✓] AVAILABLE   Operating System         : Linux-6.6.0-kali-amd64 (Kali Linux)

[Storage]
  [✓] AVAILABLE   SQLite3 Support          : SQLite version 3.45.1 (WAL mode supported)

[Datasets]
  [✓] AVAILABLE   Local OUI Database       : Found data/oui/oui.csv (100% offline)

[Wi-Fi Tools]
  [✓] AVAILABLE   NetworkManager (nmcli)   : Binary at /usr/bin/nmcli
  [✓] AVAILABLE   nl80211 Tool (iw)        : Binary at /usr/bin/iw

[Hardware]
  [✓] AVAILABLE   Wi-Fi Interfaces         : Found: wlan0 (UP)
  [✓] AVAILABLE   Bluetooth Adapters       : Found: hci0
═══════════════════════════════════════════════════════════════════════════
```

---

## 22. Troubleshooting

| Issue | Cause | Solution |
|---|---|---|
| **No Wi-Fi observations appearing** | Interface is down or unmanaged | Run `nmcli device` or `sudo ip link set wlan0 up`. Alternatively use `./run.sh --mock`. |
| **BLE scanning returns no results** | Bluetooth service stopped or adapter missing | Ensure BlueZ is active (`sudo systemctl start bluetooth`). |
| **Port 8000 already in use** | Another service is using port 8000 | Launch with `--port 8080`: `./run.sh --port 8080`. |
| **Audio alerts silent** | Browser audio permissions / default mute | Click the **🔊 AUDIO** button in the top ribbon to enable Web Audio synthesis. |

---

## 23. Privacy Architecture

- **Zero Cloud Telemetry**: All data remains on the local machine (`127.0.0.1`).
- **No Third-Party Analytics**: Zero external tracking scripts or CDN calls.
- **Local Storage**: All observations reside in a local SQLite file (`data/app.db`).

---

## 24. Security Architecture

- **Untrusted Input Sanitization**: All broadcast SSIDs and advertised names are sanitized and HTML-escaped.
- **SQL Injection Defenses**: 100% parameterized SQLite queries.
- **Subprocess Safety**: Command arguments are passed strictly as argument lists (`shell=False`).
- **Default Binding**: Binds strictly to `127.0.0.1` (localhost).

---

## 25. Known Limitations

1. **RSSI $\neq$ Exact Distance**: Physical obstacles, walls, and multipath interference affect signal attenuation.
2. **Radar Angle $\neq$ Bearing**: Angle on the scope is a deterministic hash for display clustering, not radio direction finding.
3. **MAC Randomization**: Devices with Locally Administered addresses change identifiers periodically.

---

## 26. Development & Contributing

Contributions are welcome! Please follow these standards:
- Format code with standard Python conventions.
- Maintain strict typing annotations.
- Add unit tests in `tests/` for new classifiers or parsers.

---

## 27. Automated Testing

Run the complete test suite with `pytest`:
```bash
pytest
```
Run with coverage:
```bash
pytest -v --asyncio-mode=auto
```

---

## 28. Deployment & Optional Systemd Service

For headless remote field observation nodes, configure an optional systemd service:

`/etc/systemd/system/signal-observer.service`:
```ini
[Unit]
Description=Signal Observer Passive Wireless Platform
After=network.target NetworkManager.service bluetooth.target

[Service]
Type=simple
User=kali
WorkingDirectory=/opt/signal-observer
ExecStart=/opt/signal-observer/.venv/bin/python -m application run --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now signal-observer
```

---

## 29. Roadmap

- [x] Kali Linux first-class support and pre-flight diagnostics
- [x] Modular Wi-Fi (`nmcli`, `iw`, raw) and BLE (`bleak`, `bluez`) scanner backends
- [x] Dynamic Mock simulation backend
- [x] Fast local OUI lookup database
- [x] Rule-based heuristic classification engine
- [x] Tactical HTML5 Canvas Radar with RSSI mapping
- [x] Web Audio API tactical sound alerts
- [x] Markdown Debrief, JSON, and CSV export engines
- [ ] Historical session comparison & RF differential analytics
- [ ] Optional SDR (Software Defined Radio) 433/868/915 MHz sub-GHz ingestion plugin

---

## 30. License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
