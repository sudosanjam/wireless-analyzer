"""
Unit tests for MAC normalization, string sanitization, and observation normalization.
"""

from application.utils.sanitization import (
    normalize_mac_address,
    is_locally_administered_mac,
    extract_oui_prefix,
    sanitize_string,
)
from application.engine.normalizer import (
    channel_to_frequency_and_band,
    categorize_rssi,
    ObservationNormalizer,
)
from application.models.observation import RawObservation


def test_mac_normalization():
    assert normalize_mac_address("00:11:22:33:44:55") == "00:11:22:33:44:55"
    assert normalize_mac_address("00-11-22-33-44-55") == "00:11:22:33:44:55"
    assert normalize_mac_address("0011.2233.4455") == "00:11:22:33:44:55"
    assert normalize_mac_address("001122334455") == "00:11:22:33:44:55"
    assert normalize_mac_address("aabbccddeeff") == "AA:BB:CC:DD:EE:FF"
    assert normalize_mac_address("invalid-mac") is None
    assert normalize_mac_address("") is None
    assert normalize_mac_address(None) is None


def test_locally_administered_mac():
    # Universally Administered (OUI registered)
    assert not is_locally_administered_mac("00:0C:29:4A:12:88") # Cisco
    assert not is_locally_administered_mac("B8:27:EB:11:22:33") # Raspberry Pi
    
    # Locally Administered (Bit 1 of Byte 0 is 1: x2, x6, xA, xE)
    assert is_locally_administered_mac("DA:A1:19:22:33:44")
    assert is_locally_administered_mac("02:00:00:00:00:00")
    assert is_locally_administered_mac("F6:12:34:56:78:9A")


def test_extract_oui_prefix():
    assert extract_oui_prefix("00:11:22:33:44:55") == "00:11:22"
    assert extract_oui_prefix("b8-27-eb-aa-bb-cc") == "B8:27:EB"
    assert extract_oui_prefix("invalid") is None


def test_sanitize_string():
    # HTML injection prevention
    assert sanitize_string("<script>alert(1)</script>") == "&lt;script&gt;alert(1)&lt;/script&gt;"
    # Control character removal
    assert sanitize_string("Test\x00\x01\x02SSID") == "TestSSID"
    # Truncation
    long_str = "A" * 200
    sanitized = sanitize_string(long_str, max_length=64)
    assert len(sanitized) <= 65 and sanitized.endswith("…")
    # Empty / None handling
    assert sanitize_string(None, default="Unknown") == "Unknown"
    assert sanitize_string("", default="Unknown") == "Unknown"


def test_channel_to_frequency_and_band():
    freq, band = channel_to_frequency_and_band(1)
    assert freq == 2412 and band == "2.4 GHz"

    freq, band = channel_to_frequency_and_band(6)
    assert freq == 2437 and band == "2.4 GHz"

    freq, band = channel_to_frequency_and_band(36)
    assert freq == 5180 and band == "5 GHz"

    freq, band = channel_to_frequency_and_band(149)
    assert freq == 5745 and band == "5 GHz"

    freq, band = channel_to_frequency_and_band(None, freq=5200)
    assert freq == 5200 and band == "5 GHz"


def test_categorize_rssi():
    assert categorize_rssi(-45) == "STRONG"
    assert categorize_rssi(-55) == "STRONG"
    assert categorize_rssi(-65) == "MEDIUM"
    assert categorize_rssi(-75) == "MEDIUM"
    assert categorize_rssi(-85) == "WEAK"


def test_observation_normalization_pipeline(normalizer: ObservationNormalizer):
    raw = RawObservation(
        source="wifi",
        interface="wlan0",
        raw_identifier="00:00:0C:4A:12:88",
        ssid="Corp-Enterprise-5G",
        rssi=-48,
        channel=36,
        security="WPA2-Enterprise",
        capabilities=["ESS", "HT40"],
    )
    norm = normalizer.normalize(raw, session_id="test-session-123")
    assert norm is not None
    assert norm.mac_address == "00:00:0C:4A:12:88"
    assert norm.ssid == "Corp-Enterprise-5G"
    assert norm.rssi == -48
    assert norm.rssi_category == "STRONG"
    assert norm.frequency == 5180
    assert norm.band == "5 GHz"
    assert norm.manufacturer == "Cisco Systems Inc"
    assert norm.device_category == "NETWORK_INFRASTRUCTURE"
    assert norm.session_id == "test-session-123"
