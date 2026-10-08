# Multi Camera Viewer

Multi Camera Viewer is a self-hosted, authenticated camera dashboard for Windows, Raspberry Pi OS, and desktop Linux. It displays USB webcams and compatible RTSP/HTTP/MJPEG network streams together in an adjustable browser grid. Each camera has an independent capture worker, so a disconnected source reconnects automatically without stopping the other streams.

## Features

- Add, edit, remove, name, enable, hide, and switch between cameras.
- Watch several cameras simultaneously in a 1–4-column responsive grid.
- Open any camera in a single-camera fullscreen view.
- Detect USB cameras and use Windows camera indexes or Linux `/dev/video*` devices.
- Accept RTSP, HTTP/HTTPS MJPEG, and other stream URLs supported by the installed OpenCV video backend.
- Convert every working source to browser-compatible MJPEG locally.
- Set a saved resolution and target FPS independently for every camera.
- Rotate each feed 90° right, 90° left, or 180°, and flip it horizontally, vertically, or both ways.
- Reconnect failed cameras independently with an increasing retry delay.
- Preserve camera and port settings across restarts.
- Save screenshots and recordings directly on the phone or computer viewing the dashboard—not on the Pi.
- Upgrade program files from GitHub without replacing cameras, credentials, settings, or logs.
- Show actual local, LAN, and Tailscale URLs at every launch.
- Change the saved preferred port later in Settings and display all current access URLs.
- Protect the dashboard with a password, signed session cookies, and CSRF protection.
- Configure hidden Windows sign-in startup or a Linux systemd boot service, and verify Linux is both boot-enabled and running.
- Change between Automatic and Manual startup later from the authenticated Settings drawer.

## Requirements

- Python 3.10 or newer.
- Windows 10/11, Raspberry Pi OS (64-bit recommended), or a current Linux distribution.
- A modern browser on the same device or network.
- USB webcams supported by the operating system, or reachable network-camera stream URLs.
- Tailscale must already be installed, signed in, and connected on the server and viewing devices before a Tailscale URL can be detected or used. This project does not install or configure Tailscale.

The Linux setup script installs `python3-venv`, `python3-pip`, and the distribution's `python3-opencv` package on apt-based systems. On other systems, the installer attempts to install the headless OpenCV wheel in its private environment.

## Install on Windows

1. Download or clone this repository.
2. Open PowerShell in the repository folder.
3. Run:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\setup-windows.ps1
   ```

4. Choose the installation folder, automatic or manual startup, port, and administrator username/password. The automatic/manual question is shown before dependencies are installed.
5. If autostart was declined, double-click `start-multi-camera-viewer.bat` in the selected installation folder. Keep that window open; press `Ctrl+C` to stop it.

The installer reads the Windows Known Folder location for Documents, so redirected and OneDrive-backed Documents folders are supported. It then checks likely OneDrive and user locations for an existing folder named `Documents`. If none is found, it requires you to enter a folder instead of silently choosing another location. At completion it prints the local URL, every detected LAN URL, and every detected Tailscale URL. Selecting automatic startup also starts the Windows viewer immediately in the background.

Windows autostart uses Task Scheduler with an `ONLOGON` trigger and a hidden `wscript.exe` launcher. It starts when the installing user signs in, not before sign-in and not at early system boot. No terminal window must remain open.

## Install on Raspberry Pi OS or Linux

```bash
git clone https://github.com/Sa3doonAlRa3doon/multi-camera-viewer.git
cd multi-camera-viewer
chmod +x setup-linux.sh
./setup-linux.sh
```

The script may request `sudo` to install apt dependencies and, when autostart is selected, to register `/etc/systemd/system/multi-camera-viewer.service`. The service runs as the user who performed setup, waits for the network, restarts after failures, and starts during normal system boot.

The setup asks about automatic or manual startup before installing dependencies. When systemd autostart is selected, `systemctl enable --now` starts the viewer immediately and at future boots. Setup now verifies that the service stays active; merely having an enabled but failed unit is reported as an error. The final summary prints the actual detected local, LAN, and Tailscale URLs.

If autostart was declined, start manually:

```bash
~/Documents/MultiCameraViewer/start-multi-camera-viewer.sh
```

Use the actual path printed by setup if Documents is redirected or you selected a custom folder. Keep the terminal open and press `Ctrl+C` to stop a foreground launch.

## Interactive setup and storage

The installer offers `<Documents>/MultiCameraViewer` and accepts a custom folder. Application files, its private Python environment, configuration, camera definitions, and logs all remain under that selected folder:

| Path | Purpose |
|---|---|
| `app/` | Application and browser interface |
| `.venv/` | Private Python environment |
| `config/settings.json` | Port, login hash, session secret, autostart state |
| `data/cameras.json` | Camera names, sources, and optional credentials |
| `data/server.pid` | Running-process marker |
| `logs/multi-camera-viewer.log` | Rotating application log |
| `logs/autostart.log` | Additional Windows hidden-start output |
| `backups/` | Private updater backups retained on the server |

`config/`, `data/`, `logs/`, `.env*`, and virtual environments are excluded from Git. Do not copy private runtime files into the public repository. Passwords are salted and hashed; network-camera credentials are stored locally because they are needed to reconnect to those cameras. The API redacts credentials and URL query values.

## Port selection

Setup displays this menu:

```text
Use port 8080?
[Y] Yes
[N] Enter a custom port
[A] Automatically select an available port
[D] Use the default port
```

Uppercase and lowercase responses are accepted.

- `Y` or `D` uses port 8080 if it can be bound on the configured server address. If it is occupied, automatic selection is used.
- `N` accepts exactly four numeric digits from 1000 through 9999. An occupied custom port can be replaced manually or automatically.
- `A` checks, in order: `1010, 2020, 3030, 4040, 5050, 6060, 7070, 8080, 9090, 1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000`. Duplicates are skipped. It then searches every remaining port from 1000 through 9999.
- Availability is checked on the actual bind address (`0.0.0.0` by default). The server claims the socket before startup to close the check/start race. If another process owns the saved port on a later launch, the viewer clearly reports this, selects and saves an available fallback, and prints the new URLs.

## First launch and access

Every launch prints and logs:

- application name and version;
- selected port and installation folder;
- local URL;
- every detected LAN URL;
- every detected Tailscale IPv4 URL;
- autostart status and log location;
- an actionable error and log path if startup fails.

Open the printed local URL, usually `http://127.0.0.1:8080`, and sign in using the credentials created during setup. Addresses are detected at launch; none are hard-coded.

For LAN access, open a printed `http://LAN-IP:PORT` URL from another device. Allow the selected TCP port through the operating-system firewall if necessary. For Tailscale, first confirm both devices show as connected in Tailscale, then open the printed `http://TAILSCALE-IP:PORT` URL. Do not forward this HTTP service from an internet router. Use a trusted LAN, Tailscale's encrypted network, or an HTTPS reverse proxy.

### Change the port or get a stable address

An address such as `http://192.168.1.50:1010` contains two separate parts: `192.168.1.50` is the IP address and `1010` is the port. Open **Settings → Network access** to:

- save a preferred four-digit port from 1000 through 9999, including `1010`;
- automatically choose an available port using the documented port-selection order;
- see the active port, saved next-launch port, bind address, and actual Local/LAN/Tailscale URLs;
- refresh the detected addresses after the network or Tailscale changes.

A different saved port takes effect after restarting Multi Camera Viewer. The existing page stays available on its current port until that restart. With Linux systemd autostart enabled, restart using:

```bash
sudo systemctl restart multi-camera-viewer.service
```

For manual mode, stop the current foreground process with `Ctrl+C`, then run `./start-multi-camera-viewer.sh` from the installation folder. On Windows, stop and launch the viewer again using its launcher or management commands.

The viewer deliberately binds to `0.0.0.0`, meaning all assigned LAN and Tailscale addresses work at the same time. It cannot safely assign a permanent IP address to the operating system. For a stable LAN address, create a DHCP reservation for the Raspberry Pi in the router. For remote private access, a connected Tailscale device keeps its Tailscale identity and the viewer displays its detected Tailscale IPv4 URL. Port availability is still verified at every launch; if the saved port is occupied, the existing automatic fallback rules apply.

## Add and use cameras

Open **Settings** on the right, then choose **Detect USB cameras** or **Add camera**.

### USB webcams

- Windows typically identifies cameras using indexes such as `0`, `1`, and `2`.
- Linux and Raspberry Pi OS typically use `/dev/video0`, `/dev/video1`, and similar device paths.
- USB detection probes currently available devices. A camera already locked exclusively by another program may not appear or open.

### RTSP cameras

Use a vendor-provided RTSP stream such as `rtsp://camera-address:554/stream1`. Put the username and password in the separate credential fields instead of embedding them in the URL. Exact paths vary by manufacturer.

### HTTP and MJPEG cameras

Use the full HTTP/HTTPS MJPEG or video-stream URL. Snapshot-only JPEG URLs are not continuous video sources. URLs containing access tokens are saved only in the private data file and their query values are redacted in the interface.

Use each camera's **Show in grid** switch to swap visible cameras without deleting them. Move the Grid slider from one to four columns. Choose **Fullscreen** on a card for a single-camera view; exit with `Esc`.

### Resolution, FPS, rotation, and flip

The Add/Edit Camera dialog saves video adjustments separately for each camera:

- **Output resolution:** keep the source/original size, choose a common preset from 640 × 480 through 4K, or enter a custom width and height from 160 × 120 through 3840 × 2160.
- **Target FPS:** enter `0` to keep the source rate, or cap browser delivery from 1 through 60 frames per second. This can reduce Pi CPU and network use, but it cannot create frames beyond the camera's actual frame rate.
- **Rotate:** normal, 90° right, 90° left, or 180° upside down.
- **Flip:** none, horizontal/mirror, vertical, or both horizontal and vertical.

For USB cameras, the viewer asks the device driver for the selected resolution and FPS when supported. It also resizes and frame-limits the browser output, so the selected output still applies when a driver or a network stream ignores the request. Resizing occurs before rotation, so a 1280 × 720 image rotated 90° is displayed as 720 × 1280. Flipping is applied after rotation using the displayed image's horizontal and vertical directions. These adjustments also appear in client-side screenshots and recordings.

### Screenshots and recordings

Each camera card has **Screenshot**, **Record**, and **Fullscreen** controls.

- **Screenshot** saves a timestamped JPEG through the browser's download system.
- **Record** starts a browser-side WebM recording. Choose **Stop & save** to finish and automatically download it.
- The files are created on the device viewing the dashboard—your laptop, phone, or tablet. They are not uploaded to or stored on the Raspberry Pi.
- The browser controls the final Downloads folder and may show its normal download prompt. MediaRecorder/WebM support is required for recording; current Chromium, Chrome, Edge, and Firefox versions are recommended.

## Upgrade without losing data

After installing version 1.1.0 or newer, use the updater inside the selected installation folder.

Windows: double-click `update-multi-camera-viewer.bat`, or run:

```powershell
.\.venv\Scripts\python.exe manage.py check-update
.\.venv\Scripts\python.exe manage.py update
```

Linux/Raspberry Pi OS:

```bash
./update-multi-camera-viewer.sh
# or:
./.venv/bin/python manage.py check-update
./.venv/bin/python manage.py update
```

The updater compares the installed `VERSION` with the version on this repository's `main` branch. When a newer semantic version is available, it:

1. Stops the running viewer safely.
2. Downloads the GitHub source archive over HTTPS and validates its layout and version.
3. Creates code and private-data ZIP backups under `backups/`.
4. Replaces program files only. It never replaces `config/`, `data/`, or `logs/`.
5. Installs updated Python dependencies.
6. Restores the previous code automatically if dependency installation fails.
7. Restarts the viewer when it was running before the update. On Linux, an enabled autostart installation is regenerated, started through systemd, and health-checked instead of being silently restarted as a manual process.

For an existing 1.0.0 installation that does not yet have the updater, download the current repository and run the current setup script once, selecting the same installation folder. Existing private settings and cameras are detected and preserved. Future versions can then use the update launcher.

To publish a new version as the maintainer, update the root `VERSION` file to a higher `major.minor.patch` value, test, and publish all changes together to `main`. Do not publish a new `VERSION` value before its matching code is present.

## Manual control and autostart

Open the right-side **Settings** drawer and use **Automatic startup → Automatic** or **Manual** to change the startup mode at any time. The status is read from the real Windows Task Scheduler entry or Linux systemd service—not only from a saved preference. Linux separately reports whether the service is enabled for boot and whether it is actually running. An enabled-but-inactive or failed service is clearly marked **repair required**.

Windows can normally apply the selection immediately for the current user. Installing or changing a system service on Raspberry Pi OS/Linux requires administrator approval. The web Settings panel first attempts a safe non-interactive change; if approval or repair is needed, it displays the exact command to run in the Pi terminal. That command stops a manually running copy, rebuilds the unit with the current installation path, enables and starts it, and verifies that it remains active. The browser can disconnect briefly while ownership moves to systemd. Reopen the viewer and select **Refresh startup status**. The terminal command uses the installed folder and its private Python environment.

The same controls remain available from a terminal. Run these commands from the selected installation folder with its private Python interpreter.

Windows:

```powershell
.\.venv\Scripts\python.exe manage.py status
.\.venv\Scripts\python.exe manage.py start
.\.venv\Scripts\python.exe manage.py stop
.\.venv\Scripts\python.exe manage.py enable-autostart
# Disable and stop the registered service/task:
.\.venv\Scripts\python.exe manage.py disable-autostart
# Or disable future startup while keeping this session running:
.\.venv\Scripts\python.exe manage.py disable-autostart --keep-running
.\.venv\Scripts\python.exe manage.py remove-autostart
```

Linux/Raspberry Pi OS:

```bash
./.venv/bin/python manage.py status
./.venv/bin/python manage.py start
./.venv/bin/python manage.py stop
./.venv/bin/python manage.py enable-autostart
# Disable and stop the systemd service:
./.venv/bin/python manage.py disable-autostart
# Or disable future startup while keeping this session running:
./.venv/bin/python manage.py disable-autostart --keep-running
./.venv/bin/python manage.py remove-autostart
```

On Linux, `enable-autostart` is also the repair command: it regenerates a systemd-compatible absolute `WorkingDirectory`, and success means the unit is enabled for boot and the viewer is currently running under systemd. `disable-autostart` disables and stops the registration. Add `--keep-running` to change future startup without stopping the current Linux systemd service. `remove-autostart` also removes it; on Linux it deletes the systemd unit after disabling it. On Windows both remove the scheduled task because Task Scheduler has no useful retained-but-disabled workflow in this installer.

### Repair an existing Raspberry Pi/Linux installation

Upgrade first, then run the repair command from your actual selected installation folder:

```bash
cd ~/Documents/MultiCameraViewer
./update-multi-camera-viewer.sh
./.venv/bin/python manage.py enable-autostart
./.venv/bin/python manage.py status
```

Use the folder printed by setup or displayed in the startup information if you chose a different location. A successful repair prints `enabled at boot and running now`. Confirm it directly with:

```bash
sudo systemctl status multi-camera-viewer.service --no-pager --full
```

## Troubleshooting

- **Camera stays disconnected:** verify its USB device/index or network URL in Settings. Test network reachability and credentials. The status badge shows the latest failure and retry delay.
- **RTSP opens in the vendor app but not here:** try the camera's substream, H.264 mode, or TCP-compatible RTSP URL. Codec support depends on the OpenCV/FFmpeg components available for the platform. H.265 support varies.
- **High Raspberry Pi CPU use:** choose a lower output resolution and target FPS in Edit Camera, use the camera's lower-resolution substream, or display fewer simultaneous feeds. Every active source is decoded and re-encoded as MJPEG.
- **USB camera is busy:** close video-call, browser, or recording applications that may own it, then refresh detection or restart the viewer.
- **Remote page does not open:** confirm the printed LAN/Tailscale address is still assigned, the service is running, and the selected port is allowed through the host firewall.
- **No Tailscale URL is printed:** install Tailscale separately, sign in, connect it on both the Pi/server and viewing device, and restart Multi Camera Viewer. The application binds to `0.0.0.0`, so a detected Tailscale IPv4 address is immediately usable unless a host firewall blocks the selected port.
- **Recording does not start:** use a current Chromium/Chrome/Edge/Firefox browser. Screenshot still works where canvas downloads are supported. Safari's WebM recording support varies by version.
- **Updater reports no update:** confirm the repository's root `VERSION` was increased and all matching code was published to `main`.
- **Saved port changed:** another process owned it at launch. Read the startup output/log for the automatically selected and saved fallback.
- **Autostart is enabled but did not start:** run `./.venv/bin/python manage.py enable-autostart` from the selected installation folder. It rebuilds the unit, resolves a manual-process port conflict, starts systemd, and verifies the result. Then inspect `logs/multi-camera-viewer.log`, `sudo systemctl status multi-camera-viewer.service --no-pager --full`, or `sudo journalctl -u multi-camera-viewer.service -n 100 --no-pager` if it still fails.

## Compatibility limitations

- The viewer has no audio path; it displays video only.
- Browser output is MJPEG for broad compatibility, not direct WebRTC/HLS. Bandwidth grows with resolution, frame rate, and the number of viewers.
- Network-stream compatibility depends on the protocol, codec, authentication scheme, and OpenCV backend available on the host.
- Some USB devices allow only one process to open them.
- The built-in server is HTTP. See [SECURITY.md](SECURITY.md) before using an untrusted network.
- Raspberry Pi OS 32-bit environments may need distribution-provided `python3-opencv`; 64-bit Raspberry Pi OS is recommended.

## Verification

The automated suite covers port validation and exact selection order, authenticated preferred-port changes, current LAN/Tailscale URL reporting, occupied saved-port fallback/persistence, settings persistence, login/CSRF enforcement, credential redaction, camera CRUD, per-camera video setting validation, frame resizing/rotation/flipping, USB capture requests, two concurrent capture workers, disconnect/reconnect recovery, generated Windows/systemd autostart definitions, enabled-versus-active Linux status, start-and-health verification, authenticated Automatic/Manual startup controls and Linux permission fallback, client-side capture controls, safe update archives, and private-data preservation during updates.

Run it with:

```bash
python -m pip install -r requirements-dev.txt "opencv-python-headless>=4.8,<5"
python -m pytest
python -m compileall -q app setup.py manage.py
```

Windows runtime and browser checks are performed before release. GitHub Actions repeats the unit suite on Windows and Ubuntu with Python 3.10 and 3.12. Physical Raspberry Pi boot, systemd registration, real RTSP vendor devices, and every possible USB camera/codec cannot be simulated in the development environment and must be confirmed on the target hardware.

## Uninstall

1. Run `manage.py remove-autostart` using the platform command above.
2. Run `manage.py stop` if the server is still running.
3. Back up `data/cameras.json` only if you intentionally want to retain its private camera definitions and credentials.
4. Delete the selected `MultiCameraViewer` installation folder. The original cloned/downloaded repository can be deleted separately.

The installer changes no global configuration except apt packages requested by `setup-linux.sh` and the autostart registration you approve.
