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
