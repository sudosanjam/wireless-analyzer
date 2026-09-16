"""
Evidence-based Device Classification and Priority Assignment Engine.
"""

from dataclasses import dataclass, field
from typing import Any
from application.detection.oui import OUILookupEngine
from application.detection.signatures import SignatureRegistry, SignatureRule
from application.utils.logging import get_logger

logger = get_logger("classifier")


@dataclass
class ClassificationResult:
    category: str
    confidence: float
    reason: str
    evidence: list[str] = field(default_factory=list)
    priority: str = "INFO"


class DeviceClassifier:
    """
    Evaluates observed wireless metadata against local OUI records and signature rules.
    Outputs transparent, evidence-based heuristic classifications.
    """

    def __init__(
        self,
        oui_engine: OUILookupEngine | None = None,
        signatures: SignatureRegistry | None = None,
    ) -> None:
        self.oui_engine = oui_engine or OUILookupEngine()
        self.signatures = signatures or SignatureRegistry()

    def classify(
        self,
        mac_address: str | None,
        ssid: str | None = None,
        device_name: str | None = None,
        capabilities: list[str] | None = None,
        service_uuids: list[str] | None = None,
        source: str = "wifi",
    ) -> ClassificationResult:
        """
        Perform multi-factor evidence classification.
        """
        evidence: list[str] = []
        caps = [c.lower() for c in (capabilities or [])]
        uuids = [u.lower() for u in (service_uuids or [])]
        norm_ssid = (ssid or "").strip()
        norm_name = (device_name or "").strip()

        # Step 1: OUI / Manufacturer Lookup
        oui_result = self.oui_engine.lookup(mac_address)
        manufacturer = oui_result.manufacturer
        
        if oui_result.is_randomized:
            evidence.append("MAC address has Locally Administered bit set (randomized)")
        elif oui_result.is_known:
            evidence.append(f"OUI prefix {oui_result.oui_prefix} registered to '{manufacturer}'")

        # Step 2: Evaluate Signature Rules
        best_rule: SignatureRule | None = None
        best_rule_matches = 0
        best_confidence = 0.0

        for rule in self.signatures.rules:
            matched = False
            matches_count = 0

            # Manufacturer match
            if rule.manufacturer_contains and manufacturer != "Unknown":
                man_lower = manufacturer.lower()
                if any(m in man_lower for m in rule.manufacturer_contains):
                    matched = True
                    matches_count += 1

            # SSID regex match
            if rule._compiled_ssid and norm_ssid:
                if rule._compiled_ssid.search(norm_ssid):
                    matched = True
                    matches_count += 2  # Specific SSID pattern carries high weight

            # Device Name regex match
            if rule._compiled_device_name and norm_name:
                if rule._compiled_device_name.search(norm_name):
                    matched = True
                    matches_count += 2

            # Service UUIDs match
            if rule.service_uuids and uuids:
                if any(u in uuids for u in rule.service_uuids):
                    matched = True
                    matches_count += 2

            # Capabilities match
            if rule.capabilities_contains and caps:
                if any(c in caps for c in rule.capabilities_contains):
                    matched = True
                    matches_count += 1

            if matched:
                if matches_count > best_rule_matches or (
                    matches_count == best_rule_matches and rule.confidence > best_confidence
                ):
                    best_rule = rule
                    best_rule_matches = matches_count
                    best_confidence = rule.confidence

        if best_rule:
            evidence.append(f"Matched signature rule '{best_rule.name}' ({best_rule.reason})")
            
            # Compute heuristic priority
            priority = "INFO"
            if best_rule.category in ("NETWORK_INFRASTRUCTURE", "ROUTER_GATEWAY"):
                priority = "LOW"
            elif best_rule.category in ("IOT_EMBEDDED", "COMMERCIAL_HARDWARE"):
                priority = "MEDIUM"

            return ClassificationResult(
                category=best_rule.category,
                confidence=min(1.0, round(best_confidence, 2)),
                reason=best_rule.reason,
                evidence=evidence,
                priority=priority,
            )

        # Step 3: Heuristic fallbacks if no explicit rule matched
        if source == "ble":
            if norm_name:
                evidence.append(f"BLE advertised name present: '{norm_name}'")
            return ClassificationResult(
                category="MOBILE_DEVICE" if oui_result.is_randomized else "PERIPHERAL_OR_BEACON",
                confidence=0.45 if oui_result.is_randomized else 0.35,
                reason="Unmatched BLE advertising beacon or mobile device",
                evidence=evidence,
                priority="INFO",
            )
        
        if source == "wifi":
            if norm_ssid:
                evidence.append(f"Wi-Fi Access Point broadcasting SSID '{norm_ssid}'")
                return ClassificationResult(
                    category="ACCESS_POINT",
                    confidence=0.55,
                    reason="Standard Wi-Fi Access Point beacon broadcast",
                    evidence=evidence,
                    priority="LOW",
                )
            else:
                evidence.append("Hidden SSID Wi-Fi beacon")
                return ClassificationResult(
                    category="ACCESS_POINT",
                    confidence=0.50,
                    reason="Wi-Fi Access Point with hidden/suppressed SSID",
                    evidence=evidence,
                    priority="LOW",
                )

        return ClassificationResult(
            category="UNKNOWN",
            confidence=0.0,
            reason="Insufficient metadata to establish device category",
            evidence=evidence,
            priority="INFO",
        )
