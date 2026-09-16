"""
Linux nl80211 (iw) Wi-Fi observation backend.
Parses kernel wireless survey tables and passive scan dumps.
"""

from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import Any
from application.models.observation import RawObservation
from application.scanners.base import BaseScannerBackend
from application.utils.logging import get_logger

logger = get_logger("scanner.iw")


class IWBackend(BaseScannerBackend):
    """
    Wi-Fi Scanner backend using `iw dev <iface> scan dump`.
    """

    def __init__(self, interface: str = "wlan0", config: dict[str, Any] | None = None) -> None:
        super().__init__(interface, config)
        self._bin = shutil.which("iw")

    def is_available(self) -> bool:
        return self._bin is not None and self.interface != "auto"

    def start(self) -> None:
        self.is_running = True
        logger.info("Started IW Wi-Fi scanner backend on interface '%s'", self.interface)

    def stop(self) -> None:
        self.is_running = False

    def scan(self) -> list[RawObservation]:
        if not self.is_running or not self._bin:
            return []

        observations: list[RawObservation] = []
        cmd = [self._bin, "dev", self.interface, "scan", "dump"]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if res.returncode != 0:
                return []

            now = time.time()
            current_bssid = None
            current_ssid = None
            current_freq = None
            current_rssi = -90
            current_caps: list[str] = []

            for line in res.stdout.splitlines():
                stripped = line.strip()
                if stripped.startswith("BSS "):
                    # Save previous BSS if exists
                    if current_bssid:
                        observations.append(
                            self._build_raw_obs(
                                current_bssid, current_ssid, current_freq,
                                current_rssi, current_caps, now
                            )
                        )
                    # Start new BSS
                    # Format: "BSS 00:11:22:33:44:55(on wlan0)"
                    match = re.search(r"BSS ([0-9a-fA-F:]{17})", stripped)
                    current_bssid = match.group(1) if match else None
                    current_ssid = None
                    current_freq = None
                    current_rssi = -90
                    current_caps = []

                elif stripped.startswith("freq:"):
                    try:
                        current_freq = int(stripped.split()[1])
                    except Exception:
                        pass
                elif stripped.startswith("signal:"):
                    try:
                        # Format: "signal: -54.00 dBm"
                        val_str = stripped.split()[1].replace("dBm", "")
                        current_rssi = int(float(val_str))
                    except Exception:
                        pass
                elif stripped.startswith("SSID:"):
                    raw_s = stripped[5:].strip()
                    current_ssid = raw_s if raw_s else None
                elif stripped.startswith("capability:"):
                    current_caps.extend(stripped.split()[1:])

            # Append last BSS
            if current_bssid:
                observations.append(
                    self._build_raw_obs(
                        current_bssid, current_ssid, current_freq,
                        current_rssi, current_caps, now
                    )
                )

        except Exception as e:
            logger.debug("IW scan failed: %s", e)

        return observations

    def _build_raw_obs(
        self,
        bssid: str,
        ssid: str | None,
        freq: int | None,
        rssi: int,
        caps: list[str],
        timestamp: float,
    ) -> RawObservation:
        # Calculate approximate channel from freq
        chan = None
        if freq:
            if 2412 <= freq <= 2484:
                chan = 14 if freq == 2484 else int((freq - 2407) / 5)
            elif 5180 <= freq <= 5825:
                chan = int((freq - 5000) / 5)

        return RawObservation(
            source="wifi",
            interface=self.interface,
            raw_identifier=bssid,
            timestamp=timestamp,
            ssid=ssid,
            rssi=rssi,
            channel=chan,
            frequency=freq,
            capabilities=caps,
        )
