"""
Linux NetworkManager (nmcli) Wi-Fi observation backend.
Provides non-root, non-disruptive wireless survey metadata capture.
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

logger = get_logger("scanner.nmcli")


class NMCLIBackend(BaseScannerBackend):
    """
    Wi-Fi Scanner backend using `nmcli device wifi list`.
    Does not require root permissions on Kali/Debian/Ubuntu.
    """

    def __init__(self, interface: str = "auto", config: dict[str, Any] | None = None) -> None:
        super().__init__(interface, config)
        self._bin = shutil.which("nmcli")

    def is_available(self) -> bool:
        return self._bin is not None

    def start(self) -> None:
        self.is_running = True
        logger.info("Started NMCLI Wi-Fi scanner backend on interface '%s'", self.interface)

    def stop(self) -> None:
        self.is_running = False
        logger.info("Stopped NMCLI Wi-Fi scanner backend")

    def scan(self) -> list[RawObservation]:
        if not self.is_running or not self._bin:
            return []

        observations: list[RawObservation] = []
        cmd = [
            self._bin,
            "-t",
            "-e", "yes",
            "-f", "IN-USE,BSSID,SSID,MODE,CHAN,FREQ,RATE,SIGNAL,BARS,SECURITY",
            "device", "wifi", "list",
        ]
        if self.interface != "auto":
            cmd.extend(["ifname", self.interface])

        # Active survey trigger if configured
        if self.config.get("active_survey", False):
            cmd.extend(["--rescan", "yes"])
        else:
            cmd.extend(["--rescan", "no"])

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=8,
            )
            if res.returncode != 0:
                logger.debug("nmcli returned non-zero code %d: %s", res.returncode, res.stderr)
                return []

            now = time.time()
            for line in res.stdout.strip().splitlines():
                if not line:
                    continue
                
                # Split on unescaped colons
                # In nmcli -t -e yes, colons in SSIDs or fields are escaped as \:
                parts = re.split(r"(?<!\\):", line)
                if len(parts) < 10:
                    continue

                # Unescape backslash-escapes in parts
                parts = [p.replace(r"\:", ":") for p in parts]
                
                bssid_raw = parts[1].strip()
                ssid_raw = parts[2].strip() or None
                chan_str = parts[4].strip()
                freq_str = parts[5].strip()
                signal_str = parts[7].strip()
                sec_str = parts[9].strip() or "Open"

                # Parse channel
                chan_val = None
                if chan_str.isdigit():
                    chan_val = int(chan_str)

                # Parse frequency (e.g. "2412 MHz")
                freq_val = None
                freq_match = re.search(r"(\d+)", freq_str)
                if freq_match:
                    freq_val = int(freq_match.group(1))

                # Parse signal strength: nmcli reports 0-100%
                # Map percentage to approx dBm: dBm = (signal / 2) - 100
                rssi_dbm = -90
                if signal_str.isdigit():
                    pct = int(signal_str)
                    rssi_dbm = max(-95, min(-30, int((pct / 2.0) - 100)))

                observations.append(
                    RawObservation(
                        source="wifi",
                        interface=self.interface,
                        raw_identifier=bssid_raw,
                        timestamp=now,
                        ssid=ssid_raw,
                        rssi=rssi_dbm,
                        channel=chan_val,
                        frequency=freq_val,
                        security=sec_str,
                        raw_payload={"nmcli_raw": line},
                    )
                )
        except subprocess.TimeoutExpired:
            logger.warning("nmcli scan timed out")
        except Exception as e:
            logger.error("Error executing nmcli scan: %s", e)

        return observations
