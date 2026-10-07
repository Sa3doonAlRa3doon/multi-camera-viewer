"""Platform autostart registration and status helpers."""

from __future__ import annotations

import getpass
import os
import platform
import shlex
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


def _sudo(command: list[str], non_interactive: bool) -> list[str]:
    return ["sudo", "-n", *command] if non_interactive else ["sudo", *command]


def enable_autostart(
    root: Path,
    *,
    start_now: bool = False,
    non_interactive: bool = False,
) -> tuple[bool, str]:
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
            _sudo(["install", "-m", "644", str(service_source), str(service_target)], non_interactive),
            _sudo(["systemctl", "daemon-reload"], non_interactive),
            _sudo(
                ["systemctl", "enable", *(["--now"] if start_now else []), LINUX_SERVICE_NAME],
                non_interactive,
            ),
        ]
        for command in commands:
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                return False, (result.stderr or result.stdout).strip()
        return True, "systemd system service (starts at boot)"
    return False, f"Automatic startup is not supported on {system}."


def disable_autostart(
    root: Path,
    remove: bool = False,
    *,
    stop_now: bool = True,
    non_interactive: bool = False,
) -> tuple[bool, str]:
    del root
    system = platform.system()
    if system == "Windows":
        command = ["schtasks", "/Delete", "/TN", WINDOWS_TASK_NAME, "/F"]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        return result.returncode == 0, (result.stderr or result.stdout).strip()
    if system == "Linux":
        command = _sudo(
            ["systemctl", "disable", *(["--now"] if stop_now else []), LINUX_SERVICE_NAME],
            non_interactive,
        )
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode == 0 and remove:
            target = Path("/etc/systemd/system") / LINUX_SERVICE_NAME
            subprocess.run(_sudo(["rm", "-f", str(target)], non_interactive), check=False)
            subprocess.run(_sudo(["systemctl", "daemon-reload"], non_interactive), check=False)
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


def autostart_info() -> dict[str, object]:
    system = platform.system()
    status = autostart_status()
    descriptions = {
        "Windows": "Automatic starts at user sign-in using Windows Task Scheduler.",
        "Linux": "Automatic starts at system boot using a systemd service.",
    }
    return {
        "enabled": status.startswith("enabled"),
        "status": status,
        "platform": system,
        "description": descriptions.get(system, f"Automatic startup is not supported on {system}."),
        "supported": system in {"Windows", "Linux"},
    }


def autostart_terminal_command(root: Path, enabled: bool) -> str:
    if platform.system() == "Windows":
        command = "enable-autostart" if enabled else "disable-autostart --keep-running"
        return rf'.\.venv\Scripts\python.exe manage.py {command}'
    command = "enable-autostart" if enabled else "disable-autostart --keep-running"
    linux_root = str(root).replace("\\", "/")
    return f"cd {shlex.quote(linux_root)} && ./.venv/bin/python manage.py {command}"
