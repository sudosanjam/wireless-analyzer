"""
Signature rules loader and matcher for device classification.
"""

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any
import yaml
from application.utils.logging import get_logger

logger = get_logger("signatures")


@dataclass
class SignatureRule:
    name: str
    category: str
    confidence: float
    reason: str
    manufacturer_contains: list[str] = field(default_factory=list)
    ssid_regex: str | None = None
    device_name_regex: str | None = None
    service_uuids: list[str] = field(default_factory=list)
    capabilities_contains: list[str] = field(default_factory=list)
    
    _compiled_ssid: re.Pattern | None = field(default=None, repr=False)
    _compiled_device_name: re.Pattern | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.ssid_regex:
            try:
                self._compiled_ssid = re.compile(self.ssid_regex)
            except re.error as e:
                logger.warning("Invalid SSID regex '%s' in rule '%s': %s", self.ssid_regex, self.name, e)
        if self.device_name_regex:
            try:
                self._compiled_device_name = re.compile(self.device_name_regex)
            except re.error as e:
                logger.warning("Invalid device name regex '%s' in rule '%s': %s", self.device_name_regex, self.name, e)


class SignatureRegistry:
    """Loads and compiles signature matching rules from YAML."""

    def __init__(self, yaml_path: str | Path | None = None) -> None:
        self.rules: list[SignatureRule] = []
        if yaml_path:
            self.load_from_yaml(yaml_path)

    def load_from_yaml(self, yaml_path: str | Path) -> int:
        p = Path(yaml_path)
        if not p.exists():
            logger.warning("Signatures YAML file not found at %s", p)
            return 0
        
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                
            rules_list = data.get("rules", []) if isinstance(data, dict) else []
            new_rules: list[SignatureRule] = []
            
            for item in rules_list:
                match_spec = item.get("match", {})
                rule = SignatureRule(
                    name=item.get("name", "Unnamed Rule"),
                    category=item.get("category", "UNKNOWN"),
                    confidence=float(item.get("confidence", 0.5)),
                    reason=item.get("reason", "Matched signature rule"),
                    manufacturer_contains=[m.lower() for m in match_spec.get("manufacturer_contains", [])],
                    ssid_regex=match_spec.get("ssid_regex"),
                    device_name_regex=match_spec.get("device_name_regex"),
                    service_uuids=[u.lower() for u in match_spec.get("service_uuids", [])],
                    capabilities_contains=[c.lower() for c in match_spec.get("capabilities_contains", [])],
                )
                new_rules.append(rule)
                
            self.rules = new_rules
            logger.info("Loaded %d signature classification rules from %s", len(new_rules), p)
            return len(new_rules)
        except Exception as e:
            logger.error("Error loading signature rules: %s", e)
            return 0
