"""
Realistic mock wireless signal simulation backend.
Simulates multi-vendor Wi-Fi APs, BLE advertisements, signal propagation, and turnover.
"""

import random
import time
from typing import Any
from application.models.observation import RawObservation
from application.scanners.base import BaseScannerBackend


class MockScannerBackend(BaseScannerBackend):
    """
    High-fidelity dynamic mock scanner for development, testing, and hardware-less environments.
    """

    def __init__(self, interface: str = "mock-0", config: dict[str, Any] | None = None) -> None:
        super().__init__(interface, config)
        self.is_running = False
        self._iteration = 0
        
        # Base persistent simulated devices
        self._mock_wifi_nodes = [
            {
                "mac": "00:00:0C:4A:12:88",  # Cisco
                "ssid": "Corp-Enterprise-5G",
                "rssi_base": -48,
                "channel": 36,
                "frequency": 5180,
                "security": "WPA2-Enterprise",
                "capabilities": ["ESS", "HT40", "VHT80", "WPS"],
                "persistent": True,
            },
            {
                "mac": "24:5A:4C:11:88:99",  # Ubiquiti
                "ssid": "UniFi-Guest-Portal",
                "rssi_base": -58,
                "channel": 6,
                "frequency": 2437,
                "security": "WPA2-PSK",
                "capabilities": ["ESS", "HT20"],
                "persistent": True,
            },
            {
                "mac": "14:CC:20:9B:44:11",  # TP-Link
                "ssid": "TP-Link_Archer_AX50",
                "rssi_base": -62,
                "channel": 11,
                "frequency": 2462,
                "security": "WPA3-SAE",
                "capabilities": ["ESS", "HE80", "WPS"],
                "persistent": True,
            },
            {
                "mac": "28:80:88:CC:D1:22",  # Netgear
                "ssid": "NETGEAR-NightHawk-Pro",
                "rssi_base": -70,
                "channel": 149,
                "frequency": 5745,
                "security": "WPA2-PSK",
                "capabilities": ["ESS", "VHT80"],
                "persistent": True,
            },
            {
                "mac": "34:85:18:0A:BC:33",  # Espressif ESP32
                "ssid": "SmartLife_Plug_0921",
                "rssi_base": -74,
                "channel": 1,
                "frequency": 2412,
                "security": "WPA2-PSK",
                "capabilities": ["ESS"],
                "persistent": True,
            },
            {
                "mac": "DC:A6:32:44:55:66",  # Raspberry Pi
                "ssid": "pwnagotchi",          # Watchlist trigger
                "rssi_base": -65,
                "channel": 1,
                "frequency": 2412,
                "security": "Open",
                "capabilities": ["IBSS"],
                "persistent": False,          # Appears intermittently
            },
            {
                "mac": "00:1E:2A:AA:BB:CC",  # Netgear Hidden
                "ssid": None,                 # Hidden SSID
                "rssi_base": -82,
                "channel": 44,
                "frequency": 5220,
                "security": "WPA2-Enterprise",
                "capabilities": ["ESS"],
                "persistent": True,
            },
        ]

        self._mock_ble_nodes = [
            {
                "mac": "D6:4F:22:98:71:A1",  # Randomized MAC
                "name": "Apple Watch Ultra",
                "rssi_base": -60,
                "service_uuids": ["0000fd6f-0000-1000-8000-00805f9b34fb"], # Apple Exposure / Continuity
                "persistent": True,
            },
            {
                "mac": "70:9E:29:88:12:44",  # Sony
                "name": "WH-1000XM4",
                "rssi_base": -52,
                "service_uuids": ["0000110b-0000-1000-8000-00805f9b34fb"], # Audio Sink
                "persistent": True,
            },
            {
                "mac": "10:06:1C:33:44:55",  # Flipper Devices (Watchlist trigger)
                "name": "Flipper_Zero_A4",
                "rssi_base": -68,
                "service_uuids": ["0000fe95-0000-1000-8000-00805f9b34fb"],
                "persistent": False,
            },
            {
                "mac": "F2:B1:0C:44:11:22",  # Randomized mobile probe
                "name": None,
                "rssi_base": -78,
                "service_uuids": [],
                "persistent": False,
            },
        ]

    def is_available(self) -> bool:
        return True

    def start(self) -> None:
        self.is_running = True

    def stop(self) -> None:
        self.is_running = False

    def scan(self) -> list[RawObservation]:
        """Generate one simulated observation epoch."""
        if not self.is_running:
            return []
        
        self._iteration += 1
        now = time.time()
        observations: list[RawObservation] = []

        # 1. Process Simulated Wi-Fi
        for node in self._mock_wifi_nodes:
            # If not persistent, simulate intermittent presence (e.g. present every 2 iterations)
            if not node["persistent"] and (self._iteration % 3 == 0):
                continue

            # Add RF propagation jitter (-4 to +4 dBm)
            jitter = random.randint(-4, 4)
            current_rssi = node["rssi_base"] + jitter

            observations.append(
                RawObservation(
                    source="wifi",
                    interface=self.interface,
                    raw_identifier=node["mac"],
                    timestamp=now,
                    ssid=node["ssid"],
                    rssi=current_rssi,
                    channel=node["channel"],
                    frequency=node["frequency"],
                    security=node["security"],
                    capabilities=node["capabilities"],
                    raw_payload={"mock_iteration": self._iteration},
                )
            )

        # 2. Process Simulated BLE
        for bnode in self._mock_ble_nodes:
            if not bnode["persistent"] and (self._iteration % 4 == 0):
                continue

            jitter = random.randint(-5, 5)
            current_rssi = bnode["rssi_base"] + jitter

            observations.append(
                RawObservation(
                    source="ble",
                    interface="mock-hci0",
                    raw_identifier=bnode["mac"],
                    timestamp=now,
                    device_name=bnode["name"],
                    rssi=current_rssi,
                    channel=37, # BLE advertising channel
                    frequency=2402,
                    service_uuids=bnode["service_uuids"],
                    raw_payload={"mock_iteration": self._iteration},
                )
            )

        return observations
