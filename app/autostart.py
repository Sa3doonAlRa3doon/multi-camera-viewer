"""Platform autostart registration and status helpers."""

from __future__ import annotations

import getpass
import os
import platform
import subprocess
from pathlib import Path

WINDOWS_TASK_NAME = "MultiCameraViewer"
LINUX_SERVICE_NAME = "multi-camera-viewer.service"


def _systemd_quote(value: str | Path) -> str:
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def windows_task_command(root: Path) -> list[str]:
    wrapper = root / "start-hidden.vbs"
    return [
        "schtasks", "/Create", "/TN", WINDOWS_TASK_NAME, "/SC", "ONLOGON",
        "/RL", "LIMITED", "/TR", f'wscript.exe "{wrapper}"', "/F",
    ]


def linux_service_text(root: Path, username: str | None = None) -> str:
    user = username or os.environ.get("SUDO_USER") or getpass.getuser()
    python = root / ".venv" / "bin" / "python"
    return f"""[Unit]
Description=Multi Camera Viewer
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User={user}
WorkingDirectory={_systemd_quote(root)}
Environment={_systemd_quote(f"MCV_HOME={root}")}
ExecStart={_systemd_quote(python)} -m app
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
"""


def enable_autostart(root: Path) -> tuple[bool, str]:
    system = platform.system()
    if system == "Windows":
        result = subprocess.run(windows_task_command(root), capture_output=True, text=True, check=False)
        if result.returncode == 0:
            return True, "Windows Task Scheduler (starts at user sign-in)"
        return False, (result.stderr or result.stdout).strip()
    if system == "Linux":
        service_source = root / "multi-camera-viewer.service"
        service_target = Path("/etc/systemd/system") / LINUX_SERVICE_NAME
        commands = [
            ["sudo", "install", "-m", "644", str(service_source), str(service_target)],
            ["sudo", "systemctl", "daemon-reload"],
            ["sudo", "systemctl", "enable", "--now", LINUX_SERVICE_NAME],
        ]
        for command in commands:
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                return False, (result.stderr or result.stdout).strip()
        return True, "systemd system service (starts at boot)"
    return False, f"Automatic startup is not supported on {system}."


def disable_autostart(root: Path, remove: bool = False) -> tuple[bool, str]:
    del root
    system = platform.system()
    if system == "Windows":
        command = ["schtasks", "/Delete", "/TN", WINDOWS_TASK_NAME, "/F"]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        return result.returncode == 0, (result.stderr or result.stdout).strip()
    if system == "Linux":
        command = ["sudo", "systemctl", "disable", "--now", LINUX_SERVICE_NAME]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode == 0 and remove:
            target = Path("/etc/systemd/system") / LINUX_SERVICE_NAME
            subprocess.run(["sudo", "rm", "-f", str(target)], check=False)
            subprocess.run(["sudo", "systemctl", "daemon-reload"], check=False)
        return result.returncode == 0, (result.stderr or result.stdout).strip()
    return False, f"Automatic startup is not supported on {system}."


def autostart_status() -> str:
    system = platform.system()
    if system == "Windows":
        result = subprocess.run(
            ["schtasks", "/Query", "/TN", WINDOWS_TASK_NAME],
            capture_output=True, text=True, check=False,
        )
        return "enabled (user sign-in)" if result.returncode == 0 else "disabled"
    if system == "Linux":
        result = subprocess.run(
            ["systemctl", "is-enabled", LINUX_SERVICE_NAME],
            capture_output=True, text=True, check=False,
        )
        return "enabled (system boot)" if result.returncode == 0 else "disabled"
    return "unsupported"
