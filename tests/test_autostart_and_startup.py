import socket

from app.__main__ import bind_listener
from app.autostart import linux_service_text, windows_task_command
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
