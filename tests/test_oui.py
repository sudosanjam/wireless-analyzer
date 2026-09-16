"""
Unit tests for OUI lookup engine.
"""

from application.detection.oui import OUILookupEngine


def test_oui_lookup_known_vendors(oui_engine: OUILookupEngine):
    # Apple
    res = oui_engine.lookup("00:03:93:11:22:33")
    assert res.is_known
    assert "Apple" in res.manufacturer
    assert not res.is_randomized

    # Cisco
    res = oui_engine.lookup("00:00:0C:44:55:66")
    assert res.is_known
    assert "Cisco" in res.manufacturer

    # Raspberry Pi
    res = oui_engine.lookup("B8:27:EB:12:34:56")
    assert res.is_known
    assert "Raspberry Pi" in res.manufacturer

    # Espressif
    res = oui_engine.lookup("18:FE:34:AA:BB:CC")
    assert res.is_known
    assert "Espressif" in res.manufacturer


def test_oui_lookup_randomized_mac(oui_engine: OUILookupEngine):
    # DA:A1:19:xx:xx:xx has bit 1 set -> Locally Administered
    res = oui_engine.lookup("DA:A1:19:11:22:33")
    assert res.is_randomized
    assert "Randomized" in res.manufacturer
    assert not res.is_known


def test_oui_lookup_unknown_vendor(oui_engine: OUILookupEngine):
    # 00:00:00 is not in standard vendor table
    res = oui_engine.lookup("00:00:01:11:22:33")
    assert not res.is_randomized
    assert res.manufacturer == "Unknown"
    assert not res.is_known
