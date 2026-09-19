"""
Unit tests for Scanner Backends and output parsers.
"""

from application.scanners.mock_scanner import MockScannerBackend
from application.scanners.wifi_nmcli import NMCLIBackend
from application.scanners.wifi_iw import IWBackend


def test_mock_scanner_backend():
    scanner = MockScannerBackend(interface="mock-0")
    assert scanner.is_available()
    
    # Before starting, scan returns empty
    assert len(scanner.scan()) == 0

    scanner.start()
    obs = scanner.scan()
    assert len(obs) > 0
    
    # Check that we have both Wi-Fi and BLE observations
    wifi_obs = [o for o in obs if o.source == "wifi"]
    ble_obs = [o for o in obs if o.source == "ble"]
    assert len(wifi_obs) > 0
    assert len(ble_obs) > 0

    scanner.stop()
    assert len(scanner.scan()) == 0


def test_iw_parser_structure():
    backend = IWBackend(interface="wlan0")
    # Test internal builder helper
    raw = backend._build_raw_obs(
        bssid="00:11:22:33:44:55",
        ssid="Test-IW-Network",
        freq=5180,
        rssi=-54,
        caps=["ESS", "HT40"],
        timestamp=1000.0,
    )
    assert raw.raw_identifier == "00:11:22:33:44:55"
    assert raw.ssid == "Test-IW-Network"
    assert raw.channel == 36
    assert raw.frequency == 5180
    assert raw.rssi == -54


def test_bleak_scanner_structure():
    from application.scanners.ble_bleak import BleakScannerBackend
    backend = BleakScannerBackend(interface="hci0")
    # Shouldn't raise exceptions on start/stop/is_available
    available = backend.is_available()
    assert isinstance(available, bool)
    backend.start()
    assert backend.is_running is True if available else not backend.is_running
    backend.stop()
    assert backend.is_running is False


def test_bluez_parser_and_buffering():
    from application.scanners.ble_bluez import BlueZBackend
    backend = BlueZBackend(interface="hci0")
    backend.is_running = True

    # 1. Parse [NEW] Device
    backend._parse_line("[NEW] Device 4C:65:A8:D1:22:33 SmartTag Tracker", timestamp=1000.0)
    obs1 = backend.scan()
    assert len(obs1) == 1
    assert obs1[0].raw_identifier == "4C:65:A8:D1:22:33"
    assert obs1[0].device_name == "SmartTag Tracker"
    assert obs1[0].source == "ble"
    assert obs1[0].channel == 37

    # 2. Parse [CHG] Device RSSI update with ANSI codes
    backend._parse_line("\x1b[0;32m[CHG] Device 4C:65:A8:D1:22:33 RSSI: -58\x1b[0m", timestamp=1001.0)
    obs2 = backend.scan()
    assert len(obs2) == 1
    assert obs2[0].raw_identifier == "4C:65:A8:D1:22:33"
    assert obs2[0].rssi == -58
    assert obs2[0].device_name == "SmartTag Tracker"

    # 3. Buffer should be drained after scan()
    assert len(backend.scan()) == 0

