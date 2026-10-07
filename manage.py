"""Manage a completed Multi Camera Viewer installation."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import psutil

from app.autostart import autostart_status, disable_autostart, enable_autostart
from app.config import ConfigStore, application_home


def update_autostart(root: Path, enabled: bool, kind: str) -> None:
    store = ConfigStore(root)
    settings = store.load_settings()
    settings["autostart"] = enabled
    settings["autostart_kind"] = kind
    store.save_settings(settings)


def stop_server(root: Path) -> int:
    pid_path = root / "data" / "server.pid"
    if not pid_path.exists():
        print("Multi Camera Viewer is not running (no PID file found).")
        return 0
    try:
        pid = int(pid_path.read_text(encoding="ascii").strip())
        process = psutil.Process(pid)
        command = " ".join(process.cmdline()).lower()
        if "app" not in command and "multi-camera-viewer" not in command:
            raise RuntimeError("PID file does not refer to Multi Camera Viewer; refusing to stop it.")
        process.terminate()
        process.wait(timeout=10)
        print("Multi Camera Viewer stopped.")
        return 0
    except psutil.NoSuchProcess:
        pid_path.unlink(missing_ok=True)
        print("Removed a stale PID file; the server was not running.")
        return 0
    except Exception as exc:
        print(f"Could not stop Multi Camera Viewer: {exc}", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage Multi Camera Viewer")
    parser.add_argument("command", choices=["start", "stop", "status", "enable-autostart", "disable-autostart", "remove-autostart"])
    args = parser.parse_args()
    root = application_home()
    if args.command == "start":
        from app.__main__ import main as run
        return run()
    if args.command == "stop":
        return stop_server(root)
    if args.command == "status":
        print(f"Autostart: {autostart_status()}")
        pid_path = root / "data" / "server.pid"
        print(f"Server PID: {pid_path.read_text(encoding='ascii').strip() if pid_path.exists() else 'not running'}")
        return 0
    if args.command == "enable-autostart":
        ok, detail = enable_autostart(root)
        if ok:
            update_autostart(root, True, detail)
        print(detail)
        return 0 if ok else 1
    remove = args.command == "remove-autostart"
    ok, detail = disable_autostart(root, remove=remove)
    if ok:
        update_autostart(root, False, "none")
    print(detail)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
