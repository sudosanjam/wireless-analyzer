"""
Linux BlueZ / bluetoothctl BLE observation backend.
"""

from collections import deque
import re
import shutil
import subprocess
import threading
import time
from typing import Any
from application.models.observation import RawObservation
from application.scanners.base import BaseScannerBackend
from application.utils.logging import get_logger

logger = get_logger("scanner.bluez")


class BlueZBackend(BaseScannerBackend):
    """
    Passive BLE scanner backend using Linux `bluetoothctl`.
    """

    def __init__(self, interface: str = "hci0", config: dict[str, Any] | None = None) -> None:
        super().__init__(interface, config)
        self._bin = shutil.which("bluetoothctl")
        self._buffer: deque[RawObservation] = deque(maxlen=500)
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None

    def is_available(self) -> bool:
        return self._bin is not None

    def start(self) -> None:
        if not self._bin:
            return
        self.is_running = True
        logger.info("Started BlueZ bluetoothctl BLE scanner")

    def stop(self) -> None:
        self.is_running = False
        if self._proc:
            try:
                self._proc.terminate()
            except Exception:
                pass
            self._proc = None

    def scan(self) -> list[RawObservation]:
        """Query paired/cached or actively discovered devices."""
        if not self.is_running or not self._bin:
            return []

        observations: list[RawObservation] = []
        try:
            # Query known/discovered devices
            res = subprocess.run(
                [self._bin, "devices"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            now = time.time()
            for line in res.stdout.strip().splitlines():
                # Format: "Device 00:1A:7D:DA:71:0B Device_Name"
                parts = line.split(maxsplit=2)
                if len(parts) >= 2 and parts[0] == "Device":
                    mac = parts[1]
                    name = parts[2] if len(parts) > 2 else None

                    observations.append(
                        RawObservation(
                            source="ble",
                            interface=self.interface,
                            raw_identifier=mac,
                            timestamp=now,
                            device_name=name,
                            rssi=-75,
                            channel=37,
                            frequency=2402,
                        )
                    )
        except Exception as e:
            logger.debug("bluetoothctl query error: %s", e)

        return observations
