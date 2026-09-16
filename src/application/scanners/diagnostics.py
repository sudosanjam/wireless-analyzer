"""
Pre-flight environment diagnostics and capability inspector.
"""

from dataclasses import dataclass
import os
from pathlib import Path
import platform
import shutil
import sys
from typing import Any
from application.scanners.interfaces import discover_wifi_interfaces, discover_bluetooth_interfaces
from application.config.settings import find_project_root


@dataclass
class DiagnosticItem:
    category: str
    name: str
    status: str          # "AVAILABLE", "UNAVAILABLE", "WARNING", "INFO"
    details: str


def run_diagnostics() -> list[DiagnosticItem]:
    """Inspect local operating system, tooling, and wireless capabilities."""
    results: list[DiagnosticItem] = []
    root = find_project_root()

    # 1. Python Environment
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 11)
    results.append(
        DiagnosticItem(
            category="Runtime",
            name="Python Version",
            status="AVAILABLE" if py_ok else "WARNING",
            details=f"Python {py_ver} ({sys.executable})",
        )
    )

    # 2. Operating System
    distro = platform.system()
    distro_detail = platform.platform()
    is_linux = distro.lower() == "linux"
    results.append(
        DiagnosticItem(
            category="Runtime",
            name="Operating System",
            status="AVAILABLE" if is_linux else "INFO",
            details=f"{distro_detail} {'(Kali Linux reference target)' if 'kali' in distro_detail.lower() else ''}",
        )
    )

    # 3. Database
    try:
        import sqlite3
        results.append(
            DiagnosticItem(
                category="Storage",
                name="SQLite3 Support",
                status="AVAILABLE",
                details=f"SQLite version {sqlite3.sqlite_version} (WAL mode supported)",
            )
        )
    except Exception as e:
        results.append(
            DiagnosticItem(
                category="Storage",
                name="SQLite3 Support",
                status="UNAVAILABLE",
                details=str(e),
            )
        )

    # 4. OUI Database
    oui_path = root / "data" / "oui" / "oui.csv"
    if oui_path.exists():
        size_kb = oui_path.stat().st_size // 1024
        results.append(
            DiagnosticItem(
                category="Datasets",
                name="Local OUI Database",
                status="AVAILABLE",
                details=f"Found {oui_path} ({size_kb} KB, 100% offline capable)",
            )
        )
    else:
        results.append(
            DiagnosticItem(
                category="Datasets",
                name="Local OUI Database",
                status="UNAVAILABLE",
                details=f"Missing {oui_path} (Run oui update to generate)",
            )
        )

    # 5. Linux Wi-Fi Tools
    nmcli_bin = shutil.which("nmcli")
    results.append(
        DiagnosticItem(
            category="Wi-Fi Tools",
            name="NetworkManager (nmcli)",
            status="AVAILABLE" if nmcli_bin else "UNAVAILABLE",
            details=f"Binary at {nmcli_bin}" if nmcli_bin else "Not found in PATH (Standard in Kali/Ubuntu)",
        )
    )

    iw_bin = shutil.which("iw")
    results.append(
        DiagnosticItem(
            category="Wi-Fi Tools",
            name="nl80211 Tool (iw)",
            status="AVAILABLE" if iw_bin else "UNAVAILABLE",
            details=f"Binary at {iw_bin}" if iw_bin else "Not found in PATH",
        )
    )

    # 6. Wi-Fi Physical Interfaces
    wifi_ifaces = discover_wifi_interfaces()
    if wifi_ifaces:
        names = ", ".join(f"{i.name} ({'UP' if i.is_up else 'DOWN'})" for i in wifi_ifaces)
        results.append(
            DiagnosticItem(
                category="Hardware",
                name="Wi-Fi Interfaces",
                status="AVAILABLE",
                details=f"Found: {names}",
            )
        )
    else:
        results.append(
            DiagnosticItem(
                category="Hardware",
                name="Wi-Fi Interfaces",
                status="INFO",
                details="No physical Wi-Fi adapters detected (Use --mock for simulated telemetry)",
            )
        )

    # 7. Bluetooth Adapters & Tools
    bt_bin = shutil.which("bluetoothctl")
    results.append(
        DiagnosticItem(
            category="BLE Tools",
            name="BlueZ (bluetoothctl)",
            status="AVAILABLE" if bt_bin else "UNAVAILABLE",
            details=f"Binary at {bt_bin}" if bt_bin else "Not found in PATH",
        )
    )

    bt_ifaces = discover_bluetooth_interfaces()
    if bt_ifaces:
        names = ", ".join(i.name for i in bt_ifaces)
        results.append(
            DiagnosticItem(
                category="Hardware",
                name="Bluetooth Adapters",
                status="AVAILABLE",
                details=f"Found: {names}",
            )
        )
    else:
        results.append(
            DiagnosticItem(
                category="Hardware",
                name="Bluetooth Adapters",
                status="INFO",
                details="No Bluetooth HCI adapters detected (Wi-Fi scanning proceeds normally)",
            )
        )

    return results


def format_diagnostics_table(results: list[DiagnosticItem]) -> str:
    """Format diagnostic items into a clean, cross-platform terminal report."""
    lines = [
        "===========================================================================",
        "         SIGNAL OBSERVER - PRE-FLIGHT SYSTEM DIAGNOSTICS                   ",
        "===========================================================================",
    ]
    
    current_cat = ""
    for r in results:
        if r.category != current_cat:
            current_cat = r.category
            lines.append(f"\n[{current_cat}]")
            
        status_marker = {
            "AVAILABLE": "[+] AVAILABLE  ",
            "INFO":      "[i] INFO       ",
            "WARNING":   "[!] WARNING    ",
            "UNAVAILABLE":"[-] UNAVAILABLE",
        }.get(r.status, "[?] UNKNOWN    ")
        
        lines.append(f"  {status_marker} {r.name:<24} : {r.details}")
        
    lines.append("\n===========================================================================")
    return "\n".join(lines)
