"""
Unit tests for Device Classification, Confidence Calculation, and Watchlist Engine.
"""

from application.detection.classifier import DeviceClassifier
from application.detection.watchlist import WatchlistEngine


def test_classifier_infrastructure(classifier: DeviceClassifier):
    # Cisco OUI -> NETWORK_INFRASTRUCTURE
    res = classifier.classify(
        mac_address="00:00:0C:12:34:56",
        ssid="Enterprise-AP-01",
        capabilities=["ESS", "HT40"],
        source="wifi",
    )
    assert res.category == "NETWORK_INFRASTRUCTURE"
    assert res.confidence >= 0.8
    assert res.priority in ("LOW", "INFO")
    assert any("Cisco" in e for e in res.evidence)


def test_classifier_iot_module(classifier: DeviceClassifier):
    # Espressif OUI -> IOT_EMBEDDED
    res = classifier.classify(
        mac_address="24:0A:C4:11:22:33",
        ssid="SmartBulb_123",
        source="wifi",
    )
    assert res.category == "IOT_EMBEDDED"
    assert res.confidence >= 0.8
    assert res.priority == "MEDIUM"


def test_classifier_ble_peripheral(classifier: DeviceClassifier):
    res = classifier.classify(
        mac_address="70:9E:29:88:99:00",
        device_name="WH-1000XM4",
        service_uuids=["0000110b-0000-1000-8000-00805f9b34fb"],
        source="ble",
    )
    assert res.category == "AUDIO_PERIPHERAL"
    assert res.confidence >= 0.7


def test_watchlist_matching(watchlist: WatchlistEngine):
    # Test Pwnagotchi match
    res = watchlist.evaluate(
        mac_address="00:11:22:33:44:55",
        ssid="pwnagotchi",
    )
    assert res.matched
    assert res.priority == "HIGH"
    assert any("Pwnagotchi" in n for n in res.notes)

    # Test Flipper match
    res = watchlist.evaluate(
        mac_address="10:06:1C:11:22:33",
        manufacturer="Flipper Devices Inc",
    )
    assert res.matched
    assert res.priority == "HIGH"

    # Test non-match
    res = watchlist.evaluate(
        mac_address="00:11:22:33:44:55",
        ssid="Normal-Home-WiFi",
        manufacturer="Netgear",
    )
    assert not res.matched
