"""
High-performance local OUI (Organizationally Unique Identifier) lookup engine.
"""

import csv
from pathlib import Path
from typing import NamedTuple
import urllib.request
from application.utils.sanitization import normalize_mac_address, is_locally_administered_mac, extract_oui_prefix
from application.utils.logging import get_logger

logger = get_logger("oui")


class OUILookupResult(NamedTuple):
    manufacturer: str
    is_randomized: bool
    oui_prefix: str | None
    is_known: bool


class OUILookupEngine:
    """
    Local fast OUI database lookup engine.
    100% offline-capable, thread-safe, sub-millisecond lookup.
    """

    def __init__(self, csv_path: str | Path | None = None) -> None:
        self.csv_path = Path(csv_path) if csv_path else None
        self._oui_table: dict[str, str] = {}
        self._loaded: bool = False
        if self.csv_path and self.csv_path.exists():
            self.load()

    def load(self, csv_path: str | Path | None = None) -> int:
        """Load and index OUI mappings from CSV file."""
        if csv_path:
            self.csv_path = Path(csv_path)
            
        if not self.csv_path or not self.csv_path.exists():
            logger.warning("OUI database file not found at %s", self.csv_path)
            return 0
        
        count = 0
        new_table: dict[str, str] = {}
        try:
            with open(self.csv_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                for row in reader:
                    if not row or len(row) < 2:
                        continue
                    # Skip header or comments
                    raw_assignment = row[0].strip().replace("-", "").replace(":", "").upper()
                    if raw_assignment.startswith("#") or "ASSIGNMENT" in raw_assignment:
                        continue
                    
                    org_name = row[1].strip()
                    if raw_assignment and org_name:
                        new_table[raw_assignment] = org_name
                        count += 1
                        
            self._oui_table = new_table
            self._loaded = True
            logger.info("Loaded %d OUI records from %s", count, self.csv_path)
            return count
        except Exception as e:
            logger.error("Error loading OUI database: %s", e)
            return 0

    def lookup(self, mac_address: str | None) -> OUILookupResult:
        """
        Lookup manufacturer by MAC address.
        Evaluates Locally Administered (randomized) bit and indexed prefixes.
        """
        if not mac_address:
            return OUILookupResult("Unknown", False, None, False)
            
        norm_mac = normalize_mac_address(mac_address)
        if not norm_mac:
            return OUILookupResult("Unknown", False, None, False)

        is_random = is_locally_administered_mac(norm_mac)
        clean_hex = norm_mac.replace(":", "")
        prefix_24 = clean_hex[:6]
        formatted_prefix = f"{prefix_24[:2]}:{prefix_24[2:4]}:{prefix_24[4:6]}"

        if is_random:
            # If the address is randomized/locally administered, standard OUI is not universally authoritative
            return OUILookupResult(
                manufacturer="Randomized / Locally Administered",
                is_randomized=True,
                oui_prefix=formatted_prefix,
                is_known=False,
            )

        # Check in memory index
        if prefix_24 in self._oui_table:
            return OUILookupResult(
                manufacturer=self._oui_table[prefix_24],
                is_randomized=False,
                oui_prefix=formatted_prefix,
                is_known=True,
            )

        return OUILookupResult(
            manufacturer="Unknown",
            is_randomized=False,
            oui_prefix=formatted_prefix,
            is_known=False,
        )

    def update_from_ieee(self, target_path: str | Path | None = None) -> bool:
        """
        Optional online update: Download latest official IEEE CSV database.
        Note: The platform is offline-first; this method is an explicit maintenance action.
        """
        dest = Path(target_path) if target_path else self.csv_path
        if not dest:
            return False
        
        url = "https://standards-oui.ieee.org/oui/oui.csv"
        logger.info("Downloading official IEEE OUI database from %s...", url)
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            req = urllib.request.Request(url, headers={"User-Agent": "SignalObserver/0.1"})
            with urllib.request.urlopen(req, timeout=30) as response, open(dest, "wb") as out_file:
                out_file.write(response.read())
            self.load(dest)
            logger.info("Successfully updated and reloaded OUI database (%s)", dest)
            return True
        except Exception as e:
            logger.error("Failed to download IEEE OUI database: %s", e)
            return False
