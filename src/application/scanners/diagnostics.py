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

    # 7. Bluetooth Tools & Libraries
    try:
        import bleak
        bleak_ver = getattr(bleak, "__version__", "installed")
        results.append(
            DiagnosticItem(
                category="BLE Tools",
                name="Python Bleak Library",
                status="AVAILABLE",
                details=f"Bleak {bleak_ver} (Modern asynchronous cross-platform BLE)",
            )
        )
    except ImportError:
        results.append(
            DiagnosticItem(
                category="BLE Tools",
                name="Python Bleak Library",
                status="WARNING",
                details="Not installed (Run: pip install bleak)",
            )
        )

    bt_bin = shutil.which("bluetoothctl")
    results.append(
        DiagnosticItem(
            category="BLE Tools",
            name="BlueZ (bluetoothctl)",
            status="AVAILABLE" if bt_bin else "UNAVAILABLE",
            details=f"Binary at {bt_bin}" if bt_bin else "Not found in PATH (Standard on Kali/Linux)",
        )
    )

    # 8. Linux Service & Radio State (Linux only)
    if is_linux:
        # Check systemd bluetooth service
        if shutil.which("systemctl"):
            try:
                res = subprocess.run(
                    ["systemctl", "is-active", "bluetooth"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                bt_active = res.stdout.strip() == "active"
                results.append(
                    DiagnosticItem(
                        category="BLE State",
                        name="Bluetooth Service",
                        status="AVAILABLE" if bt_active else "WARNING",
                        details="Active (Running)" if bt_active else "Inactive/Stopped (Run: sudo systemctl start bluetooth)",
                    )
                )
            except Exception:
                pass

        # Check rfkill status
        if shutil.which("rfkill"):
            try:
                res = subprocess.run(
                    ["rfkill", "list", "bluetooth"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                output = res.stdout.lower()
                is_blocked = "soft blocked: yes" in output or "hard blocked: yes" in output
                if is_blocked:
                    results.append(
                        DiagnosticItem(
                            category="BLE State",
                            name="rfkill Radio Status",
                            status="WARNING",
                            details="BLOCKED by rfkill (Run: sudo rfkill unblock bluetooth)",
                        )
                    )
                else:
                    results.append(
                        DiagnosticItem(
                            category="BLE State",
                            name="rfkill Radio Status",
                            status="AVAILABLE",
                            details="Unblocked",
                        )
                    )
            except Exception:
                pass

    # 9. Bluetooth Hardware Adapters
    bt_ifaces = discover_bluetooth_interfaces()
    if bt_ifaces:
        names = ", ".join(f"{i.name}{' (' + i.mac_address + ')' if i.mac_address else ''}" for i in bt_ifaces)
        results.append(
            DiagnosticItem(
                category="Hardware",
                name="Bluetooth Adapters",
                status="AVAILABLE",
                details=f"Found: {names}",
            )
        )
    else:
        hint = "Ensure Bluetooth adapter is connected and unblocked" if is_linux else "No Bluetooth adapter detected"
        results.append(
            DiagnosticItem(
                category="Hardware",
                name="Bluetooth Adapters",
                status="INFO",
                details=f"No Bluetooth HCI adapters detected ({hint})",
            )
        )

    return results


def format_diagnostics_table(results: list[DiagnosticItem]) -> str:
    """Format diagnostic items into a clean, cross-platform terminal report."""
    lines = [
        "===========================================================================",
        "        WIRELESS ANALYZER - PRE-FLIGHT SYSTEM DIAGNOSTICS                  ",
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
