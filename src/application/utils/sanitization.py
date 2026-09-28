"""
Sanitization, JSON serialization safety, and validation utilities for untrusted wireless metadata.
"""

from collections.abc import Mapping, Sequence
from datetime import date, datetime, time as dt_time
import html
import json
from pathlib import Path
import re
from typing import Any
import uuid

# Regex to remove non-printable control characters (except common whitespace)
_CONTROL_CHAR_REGEX = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
_MAC_NORM_REGEX = re.compile(r"[^0-9A-Fa-f]")


def sanitize_string(value: str | None, max_length: int = 128, default: str = "Unknown") -> str:
    """
    Sanitize untrusted text (SSIDs, BLE advertised names, manufacturer strings).
    - Decodes escape sequences
    - Strips non-printable control characters
    - Truncates to max_length
    - Escapes HTML entities
    """
    if value is None:
        return default
    
    # Strip null bytes and non-printable control characters
    cleaned = _CONTROL_CHAR_REGEX.sub("", str(value)).strip()
    
    if not cleaned or cleaned == "\x00" * len(cleaned):
        return default
    
    # Bound maximum length to prevent DOM overflow attacks
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length] + "…"
        
    return html.escape(cleaned)


def normalize_mac_address(mac: str | None) -> str | None:
    """
    Normalize any MAC address into canonical uppercase XX:XX:XX:XX:XX:XX format.
    Returns None if the MAC is invalid or malformed.
    """
    if not mac:
        return None
    
    clean_hex = _MAC_NORM_REGEX.sub("", mac)
    if len(clean_hex) != 12:
        return None
    
    # Format as pairs of uppercase hex digits
    return ":".join(clean_hex[i:i+2].upper() for i in range(0, 12, 2))


def is_locally_administered_mac(mac: str | None) -> bool:
    """
    Determine if a MAC address has the Locally Administered Address (LAA) bit set.
    According to IEEE 802, bit 1 of the most significant byte indicates:
    - 0: Universally Administered (assigned by IEEE OUI)
    - 1: Locally Administered (randomized MAC address on iOS, Android, Windows)
    """
    if not mac:
        return False
    norm = normalize_mac_address(mac)
    if not norm:
        return False
    
    try:
        first_byte = int(norm.split(":")[0], 16)
        return (first_byte & 0x02) != 0
    except ValueError:
        return False


def extract_oui_prefix(mac: str | None) -> str | None:
    """
    Extract the 24-bit OUI prefix (XX:XX:XX) from a MAC address.
    """
    norm = normalize_mac_address(mac)
    if not norm:
        return None
    parts = norm.split(":")
    return f"{parts[0]}:{parts[1]}:{parts[2]}"


def json_serializer_default(obj: Any) -> Any:
    """
    Fallback serializer for json.dumps default parameter.
    Converts binary types (bytes/bytearray), sets, UUIDs, dates, and non-primitives to JSON-safe values.
    """
    if isinstance(obj, (bytes, bytearray, memoryview)):
        return bytes(obj).hex()
    if isinstance(obj, (set, frozenset)):
        return list(obj)
    if isinstance(obj, (datetime, date, dt_time)):
        return obj.isoformat()
    if isinstance(obj, (uuid.UUID, Path)):
        return str(obj)
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        return obj.to_dict()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


def sanitize_raw_metadata(data: Any) -> Any:
    """
    Recursively sanitize raw scanner payloads and metadata dicts.
    Converts binary bytes to hex strings, non-string dict keys to strings,
    and sets to lists to guarantee 100% JSON serializability.
    """
    if data is None or isinstance(data, (int, float, str, bool)):
        return data
    if isinstance(data, (bytes, bytearray, memoryview)):
        return bytes(data).hex()
    if isinstance(data, Mapping):
        return {str(k): sanitize_raw_metadata(v) for k, v in data.items()}
    if isinstance(data, (list, tuple, set, frozenset, Sequence)) and not isinstance(data, (str, bytes, bytearray)):
        return [sanitize_raw_metadata(item) for item in data]
    if isinstance(data, (datetime, date, dt_time)):
        return data.isoformat()
    if isinstance(data, (uuid.UUID, Path)):
        return str(data)
    return str(data)


def safe_json_dumps(obj: Any, **kwargs: Any) -> str:
    """
    Safely serialize any object or structure to a JSON string without raising TypeError on bytes or custom objects.
    """
    if "default" not in kwargs:
        kwargs["default"] = json_serializer_default
    return json.dumps(obj, **kwargs)
