import socket
from pathlib import Path

from app.__main__ import bind_listener
from app.autostart import (
    autostart_terminal_command,
    disable_autostart,
    enable_autostart,
    linux_service_text,
    windows_task_command,
)
from app.config import ConfigStore, new_settings


def test_windows_autostart_is_hidden_and_runs_at_user_sign_in(tmp_path):
    command = windows_task_command(tmp_path)
    joined = " ".join(command)
    assert "ONLOGON" in command
    assert "wscript.exe" in joined
    assert "start-hidden.vbs" in joined


def test_linux_autostart_is_boot_system_service_with_restart(tmp_path):
    text = linux_service_text(tmp_path, username="camera-user")
    assert "User=camera-user" in text
    assert "WantedBy=multi-user.target" in text
    assert "Restart=on-failure" in text
    assert "After=network-online.target" in text
    assert 'WorkingDirectory="' in text
    assert 'ExecStart="' in text


def test_web_linux_autostart_change_is_noninteractive_and_does_not_start_duplicate(monkeypatch, tmp_path):
    calls = []

    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr("app.autostart.platform.system", lambda: "Linux")
    monkeypatch.setattr("app.autostart.subprocess.run", lambda command, **kwargs: calls.append(command) or Result())
    ok, _ = enable_autostart(tmp_path, start_now=False, non_interactive=True)
    assert ok is True
    assert len(calls) == 3
    assert all(command[:2] == ["sudo", "-n"] for command in calls)
    assert "enable" in calls[-1]
    assert "--now" not in calls[-1]


def test_web_manual_mode_keeps_current_linux_viewer_running(monkeypatch, tmp_path):
    calls = []

    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr("app.autostart.platform.system", lambda: "Linux")
    monkeypatch.setattr("app.autostart.subprocess.run", lambda command, **kwargs: calls.append(command) or Result())
    ok, _ = disable_autostart(tmp_path, stop_now=False, non_interactive=True)
    assert ok is True
    assert calls == [["sudo", "-n", "systemctl", "disable", "multi-camera-viewer.service"]]


def test_linux_admin_fallback_uses_the_installed_virtual_environment(monkeypatch):
    monkeypatch.setattr("app.autostart.platform.system", lambda: "Linux")
    command = autostart_terminal_command(Path("/home/pi5/Documents/Multi Camera Viewer"), True)
    assert command == "cd '/home/pi5/Documents/Multi Camera Viewer' && ./.venv/bin/python manage.py enable-autostart"


def test_saved_occupied_port_is_replaced_and_persisted(tmp_path):
    occupied = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    occupied.bind(("127.0.0.1", 0))
    occupied.listen(1)
    port = occupied.getsockname()[1]
    store = ConfigStore(tmp_path)
    settings = new_settings(port, "127.0.0.1", "admin", "password123")
    store.save_settings(settings)
    listener = None
    try:
        listener, selected, fallback = bind_listener(store, settings)
        assert fallback is True
        assert selected != port
        assert store.load_settings()["port"] == selected
    finally:
        occupied.close()
        if listener:
            listener.close()
