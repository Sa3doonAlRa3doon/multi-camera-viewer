"use strict";

const state = { csrf: "", cameras: [], hidden: new Set(JSON.parse(localStorage.getItem("hiddenCameras") || "[]")) };
const $ = (selector) => document.querySelector(selector);
const grid = $("#camera-grid");
const dialog = $("#camera-dialog");

async function api(url, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
  if (options.method && options.method !== "GET") headers["X-CSRF-Token"] = state.csrf;
  const response = await fetch(url, { ...options, headers, credentials: "same-origin" });
  if (response.status === 401) { location.href = "/login"; throw new Error("Sign in required"); }
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try { const data = await response.json(); message = data.detail || message; } catch (_) { /* no JSON */ }
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}

function cameraFingerprint(cameras) {
  return JSON.stringify(cameras.map(({ status, ...camera }) => camera));
}

function saveHidden() { localStorage.setItem("hiddenCameras", JSON.stringify([...state.hidden])); }

function streamUrl(camera) { return `/api/cameras/${encodeURIComponent(camera.id)}/stream?t=${Date.now()}`; }

function renderGrid() {
  grid.replaceChildren();
  const visible = state.cameras.filter(camera => camera.enabled && !state.hidden.has(camera.id));
  $("#empty-state").hidden = state.cameras.length !== 0;
  for (const camera of visible) {
    const card = $("#camera-card-template").content.firstElementChild.cloneNode(true);
    card.dataset.cameraId = camera.id;
    card.classList.add(camera.status?.state || "connecting");
    const image = card.querySelector(".stream");
    image.alt = `${camera.name} live camera stream`;
    image.src = streamUrl(camera);
    image.addEventListener("error", () => setTimeout(() => { image.src = streamUrl(camera); }, 2000));
    card.querySelector(".camera-title").textContent = camera.name;
    card.querySelector(".camera-type").textContent = camera.source_type === "usb" ? "USB camera" : `${camera.source_type.toUpperCase()} stream`;
    card.querySelector(".fullscreen").addEventListener("click", () => card.requestFullscreen?.());
    grid.append(card);
  }
  updateStatuses();
}

function updateStatuses() {
  for (const camera of state.cameras) {
    const card = grid.querySelector(`[data-camera-id="${CSS.escape(camera.id)}"]`);
    if (!card) continue;
    const status = camera.status || { state: "connecting", detail: "" };
    card.classList.remove("online", "disconnected", "connecting", "reconnecting", "disabled", "stopped");
    card.classList.add(status.state);
    const label = status.state === "online" ? "Live" : status.state;
    card.querySelector(".status-text").textContent = status.detail ? `${label}: ${status.detail}` : label;
  }
}

function renderSettings() {
  const list = $("#camera-list");
  list.replaceChildren();
  for (const camera of state.cameras) {
    const row = document.createElement("div");
    row.className = "setting-camera";
    const meta = document.createElement("div");
    const name = document.createElement("strong"); name.textContent = camera.name;
    const source = document.createElement("small"); source.textContent = camera.source || "Private stream URL configured";
    meta.append(name, document.createElement("br"), source);
    const toggle = document.createElement("input"); toggle.type = "checkbox"; toggle.checked = !state.hidden.has(camera.id); toggle.title = "Show in grid";
    toggle.addEventListener("change", () => { toggle.checked ? state.hidden.delete(camera.id) : state.hidden.add(camera.id); saveHidden(); renderGrid(); });
    const actions = document.createElement("div"); actions.className = "setting-actions";
    const edit = document.createElement("button"); edit.textContent = "Edit"; edit.addEventListener("click", () => openCameraDialog(camera));
    const remove = document.createElement("button"); remove.textContent = "Remove"; remove.className = "danger"; remove.addEventListener("click", () => removeCamera(camera));
    actions.append(edit, remove); row.append(meta, toggle, actions); list.append(row);
  }
}

async function refreshCameras(force = false) {
  const next = await api("/api/cameras");
  const changed = force || cameraFingerprint(next) !== cameraFingerprint(state.cameras);
  state.cameras = next;
  if (changed) { renderGrid(); renderSettings(); } else updateStatuses();
}

function setDrawer(open) {
  $("#settings").classList.toggle("open", open);
  $("#settings").setAttribute("aria-hidden", String(!open));
  $("#settings-toggle").setAttribute("aria-expanded", String(open));
  $("#scrim").hidden = !open;
}

function updateTypeHelp() {
  const type = $("#camera-type").value;
  $("#credentials").hidden = type === "usb";
  $("#source-help").textContent = type === "usb"
    ? "Windows usually uses an index such as 0. Linux can use /dev/video0."
    : type === "rtsp"
      ? "Example: rtsp://192.168.1.50:554/stream1. Put credentials in the fields below."
      : "Use an HTTP/HTTPS MJPEG or OpenCV-compatible video stream URL.";
  $("#camera-source").placeholder = type === "usb" ? "0" : `${type}://camera-address/stream`;
}

function openCameraDialog(camera = null) {
  $("#camera-form").reset(); $("#form-error").textContent = "";
  $("#camera-id").value = camera?.id || "";
  $("#dialog-title").textContent = camera ? "Edit camera" : "Add camera";
  $("#camera-name").value = camera?.name || "";
  $("#camera-type").value = camera?.source_type || "usb";
  $("#camera-source").value = camera?.source || "";
  $("#camera-source").required = !camera;
  $("#camera-source").placeholder = camera?.source_configured ? "Leave blank to keep the saved private URL" : "0";
  $("#camera-enabled").checked = camera?.enabled ?? true;
  updateTypeHelp(); dialog.showModal();
}

async function saveCamera(event) {
  event.preventDefault();
  const id = $("#camera-id").value;
  const clear = $("#clear-credentials").checked;
  const payload = {
    name: $("#camera-name").value,
    source_type: $("#camera-type").value,
    source: $("#camera-source").value,
    username: $("#camera-username").value,
    password: $("#camera-password").value,
    enabled: $("#camera-enabled").checked,
    clear_username: clear,
    clear_password: clear,
  };
  try {
    await api(id ? `/api/cameras/${id}` : "/api/cameras", { method: id ? "PUT" : "POST", body: JSON.stringify(payload) });
    dialog.close(); await refreshCameras(true);
  } catch (error) { $("#form-error").textContent = error.message; }
}

async function removeCamera(camera) {
  if (!confirm(`Remove “${camera.name}”? This removes its locally saved settings.`)) return;
  await api(`/api/cameras/${camera.id}`, { method: "DELETE" });
  state.hidden.delete(camera.id); saveHidden(); await refreshCameras(true);
}

async function detectUsb() {
  const button = $("#detect-usb"); button.disabled = true; button.textContent = "Detecting…";
  const target = $("#detected-list"); target.replaceChildren();
  try {
    const cameras = await api("/api/detect-usb");
    if (!cameras.length) { target.textContent = "No available USB camera was detected."; return; }
    for (const detected of cameras) {
      const row = document.createElement("div"); row.className = "detected-camera";
      const text = document.createElement("div"); const title = document.createElement("strong"); title.textContent = detected.name; const source = document.createElement("small"); source.textContent = detected.source; text.append(title, document.createElement("br"), source);
      const add = document.createElement("button"); add.textContent = "Add"; add.addEventListener("click", () => { openCameraDialog(); $("#camera-name").value = detected.name; $("#camera-source").value = detected.source; });
      row.append(text, add); target.append(row);
    }
  } catch (error) { target.textContent = error.message; }
  finally { button.disabled = false; button.textContent = "Detect USB cameras"; }
}

async function initialise() {
  try {
    const session = await api("/api/session"); state.csrf = session.csrf_token; $("#version").textContent = `v${session.version}`;
    const savedColumns = Number(localStorage.getItem("gridColumns") || 2); $("#grid-size").value = String(savedColumns); document.documentElement.style.setProperty("--grid-columns", savedColumns); $("#grid-output").textContent = `${savedColumns} column${savedColumns === 1 ? "" : "s"}`;
    await refreshCameras(true); setInterval(() => refreshCameras().catch(console.error), 2500);
  } catch (error) { console.error(error); }
}

$("#grid-size").addEventListener("input", (event) => { const columns = event.target.value; document.documentElement.style.setProperty("--grid-columns", columns); $("#grid-output").textContent = `${columns} column${columns === "1" ? "" : "s"}`; localStorage.setItem("gridColumns", columns); });
$("#settings-toggle").addEventListener("click", () => setDrawer(true)); $("#settings-close").addEventListener("click", () => setDrawer(false)); $("#scrim").addEventListener("click", () => setDrawer(false));
$("#add-camera").addEventListener("click", () => openCameraDialog()); document.querySelectorAll("[data-add-camera]").forEach(button => button.addEventListener("click", () => openCameraDialog()));
$("#camera-type").addEventListener("change", updateTypeHelp); $("#camera-form").addEventListener("submit", saveCamera); $("#dialog-close").addEventListener("click", () => dialog.close()); $("#dialog-cancel").addEventListener("click", () => dialog.close());
$("#detect-usb").addEventListener("click", detectUsb); $("#logout").addEventListener("click", async () => { await api("/logout", { method: "POST" }); location.href = "/login"; });
initialise();
