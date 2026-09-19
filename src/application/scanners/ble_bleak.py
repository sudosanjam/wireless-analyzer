"""
Bleak-based asynchronous BLE advertisement observation backend.
Operates purely in passive advertising receiver mode without active connection/pairing.
"""

from collections import deque
import threading
import time
from typing import Any
from application.models.observation import RawObservation
from application.scanners.base import BaseScannerBackend
from application.utils.logging import get_logger

logger = get_logger("scanner.bleak")


class BleakScannerBackend(BaseScannerBackend):
    """
    Passive BLE scanner backend using the Python Bleak library.
    """

    def __init__(self, interface: str = "hci0", config: dict[str, Any] | None = None) -> None:
        super().__init__(interface, config)
        self._buffer: deque[RawObservation] = deque(maxlen=500)
        self._last_error_log: float = 0.0
        self._has_bleak = False
        try:
            import bleak # type: ignore
            self._has_bleak = True
        except ImportError:
            self._has_bleak = False

    def is_available(self) -> bool:
        return self._has_bleak

    def start(self) -> None:
        if not self._has_bleak:
            return
        self.is_running = True
        logger.info("Started Bleak BLE advertisement scanner")

    def stop(self) -> None:
        self.is_running = False

    def scan(self) -> list[RawObservation]:
        if not self.is_running or not self._has_bleak:
            return []

        results: list[RawObservation] = []
        try:
            import asyncio
            from bleak import BleakScanner # type: ignore

            async def _run_discover():
                kwargs: dict[str, Any] = {"timeout": 1.5, "return_adv": True}
                if self.interface and self.interface != "auto":
                    kwargs["adapter"] = self.interface
                devices = await BleakScanner.discover(**kwargs)
                return devices

            # Run in a clean ephemeral event loop or existing loop
            loop = asyncio.new_event_loop()
            try:
                discovered = loop.run_until_complete(_run_discover())
            finally:
                loop.close()

            now = time.time()
            for key, (device, adv_data) in discovered.items():
                mac = device.address
                name = adv_data.local_name or device.name
                rssi = adv_data.rssi if adv_data.rssi is not None else -90
                uuids = adv_data.service_uuids or []

                results.append(
                    RawObservation(
                        source="ble",
                        interface=self.interface,
                        raw_identifier=mac,
                        timestamp=now,
                        device_name=name,
                        rssi=rssi,
                        channel=37,
                        frequency=2402,
                        service_uuids=uuids,
                        raw_payload={"adv_flags": adv_data.service_data},
                    )
                )

        except Exception as e:
            now = time.time()
            # Throttle warning to avoid spamming logs every 2 seconds
            if now - self._last_error_log > 15.0:
                self._last_error_log = now
                err_msg = str(e)
                if "No Bluetooth adapter found" in err_msg or "NotReady" in err_msg or "Failed" in err_msg:
                    logger.warning(
                        "Bleak BLE scan failed (%s). On Kali Linux, ensure Bluetooth is active: "
                        "1) 'sudo systemctl start bluetooth', 2) 'sudo rfkill unblock bluetooth', 3) 'bluetoothctl power on'",
                        err_msg,
                    )
                else:
                    logger.warning("Bleak BLE scan error: %s", e)
            else:
                logger.debug("Bleak scan error: %s", e)

        return results

