"""
Signal Observer CLI entry point.
Commands: run, diag, export, oui, db
"""

import argparse
from pathlib import Path
import sys
import uvicorn

from application.config.settings import load_config, AppConfig
from application.scanners.diagnostics import run_diagnostics, format_diagnostics_table
from application.detection.oui import OUILookupEngine
from application.storage.database import DatabaseManager
from application.storage.repository import SignalRepository
from application.analytics.environment import EnvironmentalAnalyticsEngine
from application.exports import (
    export_contacts_to_csv,
    export_observations_to_csv,
    export_session_to_json,
    generate_markdown_debrief,
)
from application.utils.logging import setup_logging, get_logger

logger = get_logger("cli")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="wireless-analyzer",
        description="Kali Linux-First Passive Wireless Signal Observation and Environmental Analysis Platform",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: run (default)
    run_parser = subparsers.add_parser("run", help="Start the live observation engine and dashboard")
    run_parser.add_argument("--host", default="127.0.0.1", help="Dashboard host IP (default: 127.0.0.1)")
    run_parser.add_argument("--port", type=int, default=8000, help="Dashboard port (default: 8000)")
    run_parser.add_argument("--interface", "-i", default="auto", help="Wi-Fi interface (e.g. wlan0, wlan1, auto)")
    run_parser.add_argument("--ble-interface", "-b", default="auto", help="Bluetooth interface (e.g. hci0, hci1, auto)")
    run_parser.add_argument("--backend", choices=["auto", "nmcli", "iw", "raw", "mock"], default="auto", help="Wi-Fi scanner backend")
    run_parser.add_argument("--ble-backend", choices=["auto", "bleak", "bluez", "mock"], default="auto", help="BLE scanner backend")
    run_parser.add_argument("--mock", action="store_true", help="Run with simulated telemetry (no wireless hardware required)")
    run_parser.add_argument("--no-ble", action="store_true", help="Disable BLE observation")
    run_parser.add_argument("--interval", type=float, default=2.0, help="Observation scan interval in seconds")
    run_parser.add_argument("--config", "-c", help="Path to custom config.yaml")
    run_parser.add_argument("--debug", action="store_true", help="Enable verbose debug logging")

    # Command: diag
    subparsers.add_parser("diag", help="Run pre-flight environment and capability diagnostics")

    # Command: export
    export_parser = subparsers.add_parser("export", help="Export session telemetry (CSV, JSON, or Markdown Debrief)")
    export_parser.add_argument("--format", "-f", choices=["csv", "json", "debrief", "md"], default="debrief", help="Export format")
    export_parser.add_argument("--session", "-s", default="latest", help="Session ID or 'latest'")
    export_parser.add_argument("--output", "-o", help="Target output file path (defaults to stdout)")
    export_parser.add_argument("--config", "-c", help="Path to custom config.yaml")

    # Command: oui
    oui_parser = subparsers.add_parser("oui", help="Manage local IEEE OUI database")
    oui_sub = oui_parser.add_subparsers(dest="oui_action", required=True)
    oui_sub.add_parser("update", help="Download latest IEEE OUI database online")
    oui_sub.add_parser("info", help="Display local OUI database status")

    # Command: db
    db_parser = subparsers.add_parser("db", help="Database maintenance commands")
    db_sub = db_parser.add_subparsers(dest="db_action", required=True)
    prune_parser = db_sub.add_parser("prune", help="Prune historical session records")
    prune_parser.add_argument("--days", type=int, default=30, help="Retention cutoff in days (default: 30)")

    # Allow invoking with no subcommand -> default to run
    if len(sys.argv) == 1:
        args = parser.parse_args(["run"])
    elif sys.argv[1] not in subparsers.choices and not sys.argv[1].startswith("-"):
        args = parser.parse_args(["run"] + sys.argv[1:])
    else:
        args = parser.parse_args()

    if args.command == "diag":
        handle_diag()
    elif args.command == "export":
        handle_export(args)
    elif args.command == "oui":
        handle_oui(args)
    elif args.command == "db":
        handle_db(args)
    else:
        handle_run(args)


def handle_diag() -> None:
    results = run_diagnostics()
    print(format_diagnostics_table(results))


def handle_run(args: argparse.Namespace) -> None:
    # Setup config overrides
    overrides = {
        "server": {
            "host": getattr(args, "host", "127.0.0.1"),
            "port": getattr(args, "port", 8000),
            "debug": getattr(args, "debug", False),
        },
        "scanners": {
            "interface": getattr(args, "interface", "auto"),
            "ble_interface": getattr(args, "ble_interface", "auto"),
            "wifi_backend": getattr(args, "backend", "auto"),
            "ble_backend": getattr(args, "ble_backend", "auto"),
            "mock_mode": getattr(args, "mock", False),
            "scan_interval_seconds": getattr(args, "interval", 2.0),
        },
    }
    if getattr(args, "no_ble", False):
        overrides["scanners"]["ble_enabled"] = False

    config = load_config(getattr(args, "config", None), overrides)
    setup_logging(level="DEBUG" if config.server.debug else config.logging.level)

    # Print startup banner and quick diagnostic check
    print(
        r"""
 __        ___          _                  _                     _                     
 \ \      / (_)_ __ ___| | ___  ___ ___   / \   _ __   __ _  ___| |_   _ _______ _ __ 
  \ \ /\ / /| | '__/ _ \ |/ _ \/ __/ __| / _ \ | '_ \ / _` |/ / | | | | |_  / _ \ '__|
   \ V  V / | | | |  __/ |  __/\__ \__ \/ ___ \| | | | (_| | |  | |_| | |/ /  __/ |   
    \_/\_/  |_|_|  \___|_|\___||___/___/_/   \_\_| |_|\__,_|_|_| \__,_|_/___\___|_|   
                                                                                       
        PASSIVE WIRELESS SIGNAL OBSERVATION & ENVIRONMENTAL ANALYSIS
        """
    )
    print(f"[*] Platform Target : Kali Linux Reference Target")
    print(f"[*] Wi-Fi Interface : {config.scanners.interface}")
    print(f"[*] BLE Interface   : {config.scanners.ble_interface if config.scanners.ble_enabled else 'DISABLED'}")
    print(f"[*] Wi-Fi Backend   : {'MOCK SIMULATION' if config.scanners.mock_mode else config.scanners.wifi_backend}")
    print(f"[*] BLE Backend     : {'MOCK SIMULATION' if config.scanners.mock_mode else config.scanners.ble_backend}")
    print(f"[*] Wi-Fi Scanner   : {'ENABLED' if config.scanners.wifi_enabled else 'DISABLED'}")
    print(f"[*] BLE Scanner     : {'ENABLED' if config.scanners.ble_enabled else 'DISABLED'}")
    print(f"[*] Database        : {config.storage.database_path}")
    print(f"[*] Dashboard URL   : http://{config.server.host}:{config.server.port}")
    print(f"[*] Press CTRL+C to terminate cleanly.\n")

    from application.web.server import SignalObserverServer

    observer_server = SignalObserverServer(config)
    uvicorn.run(
        observer_server.app,
        host=config.server.host,
        port=config.server.port,
        log_level="info" if not config.server.debug else "debug",
    )


def handle_export(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    db = DatabaseManager(config.storage.database_path)
    repo = SignalRepository(db)

    # Resolve session
    session = None
    if args.session == "latest":
        session = repo.get_latest_session()
        if not session:
            print("[!] Error: No sessions found in database.", file=sys.stderr)
            sys.exit(1)
    else:
        session = repo.get_session(args.session)
        if not session:
            print(f"[!] Error: Session '{args.session}' not found.", file=sys.stderr)
            sys.exit(1)

    contacts = repo.get_session_contacts(session.session_id)
    events = repo.get_session_events(session.session_id)
    observations = repo.get_session_observations(session.session_id)

    fmt = args.format.lower()
    if fmt == "csv":
        output_str = export_contacts_to_csv(contacts)
    elif fmt == "json":
        output_str = export_session_to_json(session, contacts, observations, events)
    else:
        output_str = generate_markdown_debrief(session, contacts, events)

    if args.output:
        out_p = Path(args.output)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(output_str, encoding="utf-8")
        print(f"[+] Exported {fmt.upper()} to {out_p}")
    else:
        print(output_str)


def handle_oui(args: argparse.Namespace) -> None:
    config = load_config()
    engine = OUILookupEngine(config.paths.oui_database)

    if args.oui_action == "update":
        print("[*] Contacting IEEE standards database...")
        success = engine.update_from_ieee()
        if success:
            print(f"[+] Successfully downloaded and updated OUI database at {config.paths.oui_database}")
        else:
            print(f"[-] Failed to update OUI database.", file=sys.stderr)
    elif args.oui_action == "info":
        count = len(engine._oui_table)
        print(f"OUI Database: {config.paths.oui_database}")
        print(f"Loaded Records: {count}")


def handle_db(args: argparse.Namespace) -> None:
    config = load_config()
    db = DatabaseManager(config.storage.database_path)
    repo = SignalRepository(db)

    if args.db_action == "prune":
        pruned = repo.prune_retention(args.days)
        print(f"[+] Pruned {pruned} sessions older than {args.days} days.")


if __name__ == "__main__":
    main()
