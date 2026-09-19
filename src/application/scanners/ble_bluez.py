"""
Linux BlueZ / bluetoothctl BLE observation backend.
Actively executes background discovery and captures live BLE broadcast advertisements.
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

_ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
_MAC_RE = r"([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})"
_NEW_CHG_RE = re.compile(rf"(?:\[(?:NEW|CHG)\])\s+Device\s+{_MAC_RE}(?:\s+(.*))?", re.IGNORECASE)
_DEVICE_LIST_RE = re.compile(rf"^Device\s+{_MAC_RE}(?:\s+(.*))?", re.IGNORECASE)
_RSSI_RE = re.compile(r"RSSI:\s*(-?\d+)", re.IGNORECASE)
_NAME_RE = re.compile(r"(?:Name|Alias):\s*(.+)", re.IGNORECASE)


class BlueZBackend(BaseScannerBackend):
    """
    Active BLE scanner backend using Linux `bluetoothctl`.
    Spawns an interactive discovery session and buffers real-time BLE advertisements.
    """

    def __init__(self, interface: str = "hci0", config: dict[str, Any] | None = None) -> None:
        super().__init__(interface, config)
        self._bin = shutil.which("bluetoothctl")
        self._buffer: deque[RawObservation] = deque(maxlen=1000)
        self._lock = threading.Lock()
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._device_cache: dict[str, dict[str, Any]] = {}

    def is_available(self) -> bool:
        return self._bin is not None

    def start(self) -> None:
        if not self._bin:
            logger.warning("bluetoothctl binary not found in PATH")
            return
        
        if self.is_running:
            return

        self.is_running = True
        self._start_discovery_process()
        logger.info("Started BlueZ active bluetoothctl BLE scanner")

    def _start_discovery_process(self) -> None:
        """Start interactive bluetoothctl process with scan on."""
        try:
            self._proc = subprocess.Popen(
                [self._bin],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            # Send initial setup commands
            if self._proc.stdin:
                try:
                    if self.interface and self.interface != "auto":
                        self._proc.stdin.write(f"select {self.interface}\n")
                    self._proc.stdin.write("power on\n")
                    self._proc.stdin.write("scan on\n")
                    self._proc.stdin.flush()
                except Exception as e:
                    logger.debug("Failed to write initial scan commands to bluetoothctl: %s", e)

            # Start background reader thread
            self._thread = threading.Thread(target=self._reader_loop, daemon=True)
            self._thread.start()

        except Exception as e:
            logger.error("Failed to start bluetoothctl discovery process: %s", e)

    def _clean_text(self, text: str) -> str:
        """Remove ANSI color/escape codes from text."""
        return _ANSI_ESCAPE_RE.sub("", text).strip()

    def _reader_loop(self) -> None:
        """Continuous background thread reading stdout from bluetoothctl."""
        if not self._proc or not self._proc.stdout:
            return

        try:
            for raw_line in iter(self._proc.stdout.readline, ""):
                if not self.is_running:
                    break
                line = self._clean_text(raw_line)
                if not line:
                    continue
                self._parse_line(line)
        except Exception as e:
            if self.is_running:
                logger.debug("bluetoothctl reader thread exception: %s", e)
        finally:
            if self._proc and self._proc.stdout:
                try:
                    self._proc.stdout.close()
                except Exception:
                    pass

    def _parse_line(self, line: str, timestamp: float | None = None) -> None:
        """Parse a single line from bluetoothctl output and update observation buffer."""
        now = timestamp if timestamp is not None else time.time()

        # 1. Check for [NEW] / [CHG] Device ...
        match = _NEW_CHG_RE.search(line)
        if match:
            mac = match.group(1).upper()
            rest = match.group(2) or ""

            with self._lock:
                dev = self._device_cache.setdefault(mac, {
                    "name": None,
                    "rssi": -75,
                    "last_seen": now,
                })
                dev["last_seen"] = now

                # Check for RSSI change
                rssi_match = _RSSI_RE.search(rest)
                if rssi_match:
                    try:
                        dev["rssi"] = int(rssi_match.group(1))
                    except ValueError:
                        pass

                # Check for Name / Alias change
                name_match = _NAME_RE.search(rest)
                if name_match:
                    dev["name"] = name_match.group(1).strip()
                elif rest and not rssi_match and not rest.startswith(("[", "Connected:", "Paired:", "Modalias:", "UUID:")):
                    dev["name"] = rest.strip()

                self._buffer.append(
                    RawObservation(
                        source="ble",
                        interface=self.interface,
                        raw_identifier=mac,
                        timestamp=now,
                        device_name=dev["name"],
                        rssi=dev["rssi"],
                        channel=37,
                        frequency=2402,
                    )
                )
            return

        # 2. Check for Device XX:XX:XX:XX:XX:XX ... (from devices command)
        dev_match = _DEVICE_LIST_RE.match(line)
        if dev_match:
            mac = dev_match.group(1).upper()
            name = dev_match.group(2).strip() if dev_match.group(2) else None
            with self._lock:
                dev = self._device_cache.setdefault(mac, {
                    "name": name,
                    "rssi": -75,
                    "last_seen": now,
                })
                if name:
                    dev["name"] = name
                self._buffer.append(
                    RawObservation(
                        source="ble",
                        interface=self.interface,
                        raw_identifier=mac,
                        timestamp=now,
                        device_name=dev["name"],
                        rssi=dev["rssi"],
                        channel=37,
                        frequency=2402,
                    )
                )

    def stop(self) -> None:
        self.is_running = False
        if self._proc:
            try:
                if self._proc.stdin:
                    self._proc.stdin.write("scan off\nquit\n")
                    self._proc.stdin.flush()
            except Exception:
                pass
            try:
                self._proc.terminate()
            except Exception:
                pass
            self._proc = None

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
            self._thread = None

    def scan(self) -> list[RawObservation]:
        """Collect and return buffered live BLE observations."""
        if not self.is_running:
            return []

        observations: list[RawObservation] = []
        with self._lock:
            while self._buffer:
                observations.append(self._buffer.popleft())

        # If buffer was empty and discovery process died, restart it
        if not observations and self._bin and self._proc and self._proc.poll() is not None:
            logger.warning("bluetoothctl process exited unexpectedly; restarting scan")
            self._start_discovery_process()

        return observations

