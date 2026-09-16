"""
Watchlist matching engine for alert triggers.
"""

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any
import yaml
from application.utils.sanitization import normalize_mac_address
from application.utils.logging import get_logger

logger = get_logger("watchlist")


@dataclass
class WatchlistRule:
    match_type: str                  # "MAC", "OUI", "SSID_EXACT", "SSID_REGEX", "MANUFACTURER"
    pattern: str
    label: str
    priority: str = "HIGH"           # "INFO", "LOW", "MEDIUM", "HIGH"
    enabled: bool = True
    
    _compiled_regex: re.Pattern | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if "REGEX" in self.match_type.upper():
            try:
                self._compiled_regex = re.compile(self.pattern)
            except re.error as e:
                logger.warning("Invalid regex '%s' in watchlist rule '%s': %s", self.pattern, self.label, e)


@dataclass
class WatchlistMatchResult:
    matched: bool
    priority: str = "INFO"
    notes: list[str] = field(default_factory=list)


class WatchlistEngine:
    """Evaluates observations against configured watchlist items."""

    def __init__(self, yaml_path: str | Path | None = None) -> None:
        self.rules: list[WatchlistRule] = []
        if yaml_path:
            self.load_from_yaml(yaml_path)

    def load_from_yaml(self, yaml_path: str | Path) -> int:
        p = Path(yaml_path)
        if not p.exists():
            return 0
        
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                
            items = data.get("watchlist", []) if isinstance(data, dict) else []
            new_rules: list[WatchlistRule] = []
            
            for item in items:
                rule = WatchlistRule(
                    match_type=item.get("match_type", "SSID_EXACT").upper(),
                    pattern=str(item.get("pattern", "")),
                    label=str(item.get("label", "Watchlist Match")),
                    priority=str(item.get("priority", "HIGH")).upper(),
                    enabled=bool(item.get("enabled", True)),
                )
                if rule.pattern:
                    new_rules.append(rule)
                    
            self.rules = new_rules
            logger.info("Loaded %d watchlist rules from %s", len(new_rules), p)
            return len(new_rules)
        except Exception as e:
            logger.error("Error loading watchlist rules: %s", e)
            return 0

    def evaluate(
        self,
        mac_address: str | None,
        ssid: str | None = None,
        manufacturer: str | None = None,
    ) -> WatchlistMatchResult:
        """Check if observation matches any active watchlist rule."""
        norm_mac = normalize_mac_address(mac_address) or ""
        norm_ssid = (ssid or "").strip()
        norm_man = (manufacturer or "").strip().lower()

        matched = False
        highest_priority = "INFO"
        notes: list[str] = []
        
        priority_weights = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}

        for rule in self.rules:
            if not rule.enabled:
                continue

            rule_hit = False
            mtype = rule.match_type

            if mtype == "MAC" and norm_mac:
                if norm_mac.upper() == rule.pattern.upper():
                    rule_hit = True
            elif mtype == "OUI" and norm_mac:
                clean_target = rule.pattern.replace(":", "").replace("-", "").upper()
                clean_mac = norm_mac.replace(":", "")
                if clean_mac.startswith(clean_target):
                    rule_hit = True
            elif mtype == "SSID_EXACT" and norm_ssid:
                if norm_ssid.lower() == rule.pattern.lower():
                    rule_hit = True
            elif mtype == "SSID_REGEX" and norm_ssid and rule._compiled_regex:
                if rule._compiled_regex.search(norm_ssid):
                    rule_hit = True
            elif mtype == "MANUFACTURER" and norm_man:
                if rule.pattern.lower() in norm_man:
                    rule_hit = True

            if rule_hit:
                matched = True
                note = f"Watchlist: {rule.label} [{rule.pattern}]"
                notes.append(note)
                if priority_weights.get(rule.priority, 0) > priority_weights.get(highest_priority, 0):
                    highest_priority = rule.priority

        return WatchlistMatchResult(
            matched=matched,
            priority=highest_priority if matched else "INFO",
            notes=notes,
        )
