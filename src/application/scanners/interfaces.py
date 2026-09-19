"""
Hardware interface discovery for Wi-Fi and Bluetooth adapters.
"""

from pathlib import Path
import shutil
import subprocess
import sys
from application.scanners.base import InterfaceInfo
from application.utils.logging import get_logger

logger = get_logger("interfaces")


def discover_wifi_interfaces() -> list[InterfaceInfo]:
    """
    Discover Wi-Fi network interfaces on Linux via /sys/class/net and tools.
    """
    interfaces: list[InterfaceInfo] = []
    
    # 1. Inspect Linux sysfs (/sys/class/net)
    sys_net = Path("/sys/class/net")
    if sys_net.exists():
        for iface_dir in sys_net.iterdir():
            if not iface_dir.is_dir():
                continue
            name = iface_dir.name
            # Check for wireless subdirectory in sysfs
            if (iface_dir / "wireless").exists() or (iface_dir / "phy80211").exists():
                is_up = False
                operstate_file = iface_dir / "operstate"
                if operstate_file.exists():
                    try:
                        is_up = operstate_file.read_text().strip() == "up"
                    except Exception:
                        pass
                
                mac = None
                address_file = iface_dir / "address"
                if address_file.exists():
                    try:
                        mac = address_file.read_text().strip().upper()
                    except Exception:
                        pass

                interfaces.append(
                    InterfaceInfo(
                        name=name,
                        interface_type="wifi",
                        is_up=is_up,
                        mac_address=mac,
                        supported_bands=["2.4 GHz", "5 GHz"],
                    )
                )

    # 2. If sysfs check yielded nothing or not on Linux, check nmcli / iw if present
    if not interfaces and shutil.which("nmcli"):
        try:
            res = subprocess.run(
                ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            for line in res.stdout.strip().splitlines():
                parts = line.split(":")
                if len(parts) >= 3 and parts[1] == "wifi":
                    interfaces.append(
                        InterfaceInfo(
                            name=parts[0],
                            interface_type="wifi",
                            is_up=parts[2] != "unavailable",
                        )
                    )
        except Exception:
            pass

    return interfaces


def discover_bluetooth_interfaces() -> list[InterfaceInfo]:
    """
    Discover Bluetooth HCI adapters on Linux via /sys/class/bluetooth, bluetoothctl, and hciconfig.
    """
    adapters: list[InterfaceInfo] = []
    seen_names = set()
    
    # 1. Inspect Linux sysfs (/sys/class/bluetooth)
    sys_bt = Path("/sys/class/bluetooth")
    if sys_bt.exists():
        for bt_dir in sys_bt.iterdir():
            if bt_dir.is_dir() and bt_dir.name.startswith("hci"):
                mac = None
                addr_file = bt_dir / "address"
                if addr_file.exists():
                    try:
                        mac = addr_file.read_text().strip().upper()
                    except Exception:
                        pass
                name = bt_dir.name
                seen_names.add(name)
                adapters.append(
                    InterfaceInfo(
                        name=name,
                        interface_type="ble",
                        is_up=True,
                        mac_address=mac,
                    )
                )

    # 2. Check bluetoothctl if present
    if shutil.which("bluetoothctl"):
        try:
            res = subprocess.run(
                ["bluetoothctl", "list"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            for line in res.stdout.strip().splitlines():
                # Format: "Controller 00:1A:7D:DA:71:0B hci0 [default]"
                parts = line.split()
                if len(parts) >= 3 and parts[0] == "Controller":
                    name = parts[2] if len(parts) > 2 else "hci0"
                    if name not in seen_names:
                        seen_names.add(name)
                        adapters.append(
                            InterfaceInfo(
                                name=name,
                                interface_type="ble",
                                is_up=True,
                                mac_address=parts[1] if len(parts) > 1 else None,
                            )
                        )
        except Exception:
            pass

    # 3. Check hciconfig if present
    if not adapters and shutil.which("hciconfig"):
        try:
            res = subprocess.run(
                ["hciconfig"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            current_hci = None
            for line in res.stdout.splitlines():
                if line.startswith("hci"):
                    parts = line.split(":")
                    if parts:
                        current_hci = parts[0].strip()
                        if current_hci not in seen_names:
                            seen_names.add(current_hci)
                            is_up = "UP RUNNING" in line
                            adapters.append(
                                InterfaceInfo(
                                    name=current_hci,
                                    interface_type="ble",
                                    is_up=is_up,
                                )
                            )
        except Exception:
            pass

    return adapters

