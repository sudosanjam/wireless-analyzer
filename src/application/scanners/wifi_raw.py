"""
Optional Scapy Raw Socket 802.11 monitor mode sniffer backend.
Captures Beacon and Probe frames passively when an adapter is in monitor mode.
"""

from collections import deque
import threading
import time
from typing import Any
from application.models.observation import RawObservation
from application.scanners.base import BaseScannerBackend
from application.utils.logging import get_logger

logger = get_logger("scanner.raw")


class ScapyRawBackend(BaseScannerBackend):
    """
    Passive 802.11 frame sniffer for monitor mode interfaces.
    """

    def __init__(self, interface: str = "wlan0mon", config: dict[str, Any] | None = None) -> None:
        super().__init__(interface, config)
        self._buffer: deque[RawObservation] = deque(maxlen=500)
        self._thread: threading.Thread | None = None
        self._has_scapy = False
        try:
            import scapy.all # type: ignore
            self._has_scapy = True
        except ImportError:
            self._has_scapy = False

    def is_available(self) -> bool:
        return self._has_scapy and self.interface != "auto"

    def start(self) -> None:
        if not self._has_scapy:
            logger.warning("Scapy is not installed. ScapyRawBackend cannot start.")
            return

        self.is_running = True
        self._thread = threading.Thread(target=self._sniff_loop, daemon=True)
        self._thread.start()
        logger.info("Started Scapy raw monitor sniffer on '%s'", self.interface)

    def stop(self) -> None:
        self.is_running = False

    def _sniff_loop(self) -> None:
        try:
            from scapy.all import sniff, Dot11, Dot11Beacon, Dot11ProbeResp, RadioTap # type: ignore

            def _packet_handler(pkt: Any) -> None:
                if not self.is_running:
                    return
                if pkt.haslayer(Dot11Beacon) or pkt.haslayer(Dot11ProbeResp):
                    try:
                        bssid = pkt[Dot11].addr2
                        if not bssid:
                            return
                        ssid = pkt[Dot11].info.decode("utf-8", errors="replace") if hasattr(pkt[Dot11], "info") else None
                        
                        rssi = -90
                        if pkt.haslayer(RadioTap):
                            try:
                                rssi = pkt[RadioTap].dBm_AntSignal
                            except Exception:
                                pass

                        self._buffer.append(
                            RawObservation(
                                source="wifi",
                                interface=self.interface,
                                raw_identifier=bssid,
                                timestamp=time.time(),
                                ssid=ssid if ssid else None,
                                rssi=rssi,
                                capabilities=["802.11-Passive"],
                            )
                        )
                    except Exception:
                        pass

            sniff(
                iface=self.interface,
                prn=_packet_handler,
                store=0,
                stop_filter=lambda x: not self.is_running,
                timeout=1,
            )
        except Exception as e:
            logger.debug("Raw sniff loop ended: %s", e)

    def scan(self) -> list[RawObservation]:
        results: list[RawObservation] = []
        while self._buffer:
            try:
                results.append(self._buffer.popleft())
            except IndexError:
                break
        return results
