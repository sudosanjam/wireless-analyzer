"""
Observation normalization engine.
Transforms raw scanner outputs into sanitized, classified NormalizedObservation instances.
"""

from application.models.observation import RawObservation, NormalizedObservation
from application.detection.oui import OUILookupEngine
from application.detection.classifier import DeviceClassifier
from application.detection.watchlist import WatchlistEngine
from application.utils.sanitization import sanitize_string, normalize_mac_address, is_locally_administered_mac
from application.utils.logging import get_logger

logger = get_logger("normalizer")


def channel_to_frequency_and_band(channel: int | None, freq: int | None = None) -> tuple[int | None, str | None]:
    """Derive frequency (MHz) and band string from Wi-Fi channel or frequency."""
    if freq:
        if 2400 <= freq <= 2500:
            return freq, "2.4 GHz"
        elif 5000 <= freq <= 5900:
            return freq, "5 GHz"
        elif 5925 <= freq <= 7125:
            return freq, "6 GHz"
        return freq, "Unknown Band"

    if channel is None:
        return None, None

    # 2.4 GHz Channels 1-14
    if 1 <= channel <= 14:
        calc_freq = 2484 if channel == 14 else 2407 + (channel * 5)
        return calc_freq, "2.4 GHz"
    
    # 5 GHz Channels (36 to 165)
    elif 32 <= channel <= 177:
        calc_freq = 5000 + (channel * 5)
        return calc_freq, "5 GHz"
    
    # 6 GHz Channels (1 to 233 in 6GHz band)
    elif 180 <= channel <= 233:
        calc_freq = 5950 + ((channel - 1) * 5)
        return calc_freq, "6 GHz"

    return None, None


def categorize_rssi(rssi: int, strong_thresh: int = -55, med_thresh: int = -75) -> str:
    """Categorize raw RSSI dBm into human-readable buckets."""
    if rssi >= strong_thresh:
        return "STRONG"
    elif rssi >= med_thresh:
        return "MEDIUM"
    return "WEAK"


class ObservationNormalizer:
    """
    Normalizes raw scanner outputs.
    Ensures zero fabricated data, strict input sanitization, and evidence-based classification.
    """

    def __init__(
        self,
        oui_engine: OUILookupEngine | None = None,
        classifier: DeviceClassifier | None = None,
        watchlist: WatchlistEngine | None = None,
        strong_rssi: int = -55,
        medium_rssi: int = -75,
    ) -> None:
        self.oui_engine = oui_engine or OUILookupEngine()
        self.classifier = classifier or DeviceClassifier(oui_engine=self.oui_engine)
        self.watchlist = watchlist or WatchlistEngine()
        self.strong_rssi = strong_rssi
        self.medium_rssi = medium_rssi

    def normalize(self, raw: RawObservation, session_id: str = "") -> NormalizedObservation | None:
        """
        Normalize a raw observation. Returns None if the MAC/identifier is completely invalid.
        """
        norm_mac = normalize_mac_address(raw.raw_identifier)
        if not norm_mac:
            logger.debug("Discarding observation with invalid MAC/identifier: %s", raw.raw_identifier)
            return None

        is_random = is_locally_administered_mac(norm_mac)

        # Sanitize human-facing string metadata
        sanitized_ssid = sanitize_string(raw.ssid, max_length=64, default=None) if raw.ssid else None
        sanitized_name = sanitize_string(raw.device_name, max_length=64, default=None) if raw.device_name else None
        
        # Raw RSSI validation
        rssi_val = raw.rssi if raw.rssi is not None else -90
        rssi_cat = categorize_rssi(rssi_val, self.strong_rssi, self.medium_rssi)

        # Frequencies & Channels
        if raw.source == "ble":
            calc_freq, band = 2440, "BLE 2.4 GHz"
        else:
            calc_freq, band = channel_to_frequency_and_band(raw.channel, raw.frequency)

        # OUI Manufacturer Lookup
        oui_result = self.oui_engine.lookup(norm_mac)
        manufacturer = raw.manufacturer_raw or oui_result.manufacturer

        # Classification Engine
        class_result = self.classifier.classify(
            mac_address=norm_mac,
            ssid=sanitized_ssid,
            device_name=sanitized_name,
            capabilities=raw.capabilities,
            service_uuids=raw.service_uuids,
            source=raw.source,
        )

        # Watchlist Engine
        watch_result = self.watchlist.evaluate(
            mac_address=norm_mac,
            ssid=sanitized_ssid,
            manufacturer=manufacturer,
        )

        final_priority = class_result.priority
        if watch_result.matched:
            final_priority = watch_result.priority

        return NormalizedObservation(
            session_id=session_id,
            timestamp=raw.timestamp,
            source=raw.source,
            interface=raw.interface,
            mac_address=norm_mac,
            is_randomized=is_random,
            ssid=sanitized_ssid,
            bssid=norm_mac if raw.source == "wifi" else None,
            device_name=sanitized_name,
            rssi=rssi_val,
            rssi_category=rssi_cat,
            channel=raw.channel,
            frequency=calc_freq,
            band=band,
            security=raw.security,
            capabilities=raw.capabilities,
            service_uuids=raw.service_uuids,
            manufacturer=manufacturer,
            oui=oui_result.oui_prefix,
            device_category=class_result.category,
            classification_confidence=class_result.confidence,
            classification_reason=class_result.reason,
            classification_evidence=class_result.evidence,
            priority=final_priority,
            watchlist_matched=watch_result.matched,
            watchlist_notes=watch_result.notes,
            raw_metadata=raw.raw_payload,
        )
