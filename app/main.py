"""FastAPI application and authenticated camera-management API."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from starlette.middleware.sessions import SessionMiddleware

from . import __version__
from .auth import csrf_token, require_auth, require_csrf, signed_in
from .cameras import CameraManager, detect_usb_cameras, source_for_capture
from .config import ConfigStore, verify_password


class CameraPayload(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    source_type: Literal["usb", "rtsp", "http"]
    source: str = Field(default="", max_length=2048)
    username: str = Field(default="", max_length=256)
    password: str = Field(default="", max_length=512)
    enabled: bool = True
    clear_username: bool = False
    clear_password: bool = False


def _validated_camera(payload: CameraPayload, old: dict | None = None) -> dict:
    values = payload.model_dump()
    source = values["source"].strip()
    if old and (not source or "REDACTED" in source):
        source = str(old.get("source", ""))
    username = values["username"]
    password = values["password"]
    if old:
        if not username and not values["clear_username"]:
            username = str(old.get("username", ""))
        if not password and not values["clear_password"]:
            password = str(old.get("password", ""))
    camera = {
        "id": str(old["id"]) if old else str(uuid.uuid4()),
        "name": values["name"].strip(),
        "source_type": values["source_type"],
        "source": source,
        "username": "" if values["clear_username"] else username,
        "password": "" if values["clear_password"] else password,
        "enabled": values["enabled"],
    }
    if not source:
        raise HTTPException(status_code=422, detail="A camera device or stream URL is required.")
    try:
        source_for_capture(camera)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return camera


def create_app(store: ConfigStore | None = None, manager: CameraManager | None = None) -> FastAPI:
    store = store or ConfigStore()
    settings = store.load_settings()
    manager = manager or CameraManager()
    package_dir = Path(__file__).resolve().parent

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        manager.sync(store.load_cameras())
        yield
        manager.shutdown()

    app = FastAPI(title="Multi Camera Viewer", version=__version__, lifespan=lifespan)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings["session_secret"],
        same_site="lax",
        https_only=False,
        max_age=60 * 60 * 12,
    )
    app.mount("/static", StaticFiles(directory=package_dir / "static"), name="static")
    app.state.store = store
    app.state.manager = manager

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "application": "Multi Camera Viewer", "version": __version__}

    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request, error: str = ""):
        if signed_in(request):
            return RedirectResponse("/", status_code=303)
        html = (package_dir / "static" / "login.html").read_text(encoding="utf-8")
        return HTMLResponse(html.replace("{{ERROR}}", error))

    @app.post("/login")
    async def login(request: Request, username: str = Form(), password: str = Form()):
        current = store.load_settings()
        valid_user = username == current.get("username")
        valid_password = verify_password(
            password,
            str(current.get("password_salt", "")),
            str(current.get("password_hash", "")),
        )
        if not (valid_user and valid_password):
            return RedirectResponse("/login?error=Incorrect+username+or+password", status_code=303)
        request.session.clear()
        request.session["authenticated"] = True
        csrf_token(request)
        return RedirectResponse("/", status_code=303)

    @app.post("/logout")
    async def logout(request: Request, _: None = Depends(require_csrf)):
        request.session.clear()
        return {"ok": True}

    @app.get("/")
    async def index(request: Request):
        if not signed_in(request):
            return RedirectResponse("/login", status_code=303)
        return FileResponse(package_dir / "static" / "index.html", headers={"Cache-Control": "no-store"})

    @app.get("/api/session")
    async def session(request: Request, _: None = Depends(require_auth)) -> dict:
        return {"csrf_token": csrf_token(request), "version": __version__}

    @app.get("/api/cameras")
    async def list_cameras(_: None = Depends(require_auth)) -> list[dict]:
        cameras = store.load_cameras()
        manager.sync(cameras)
        statuses = manager.statuses()
        result = []
        for camera in cameras:
            public = store.public_camera(camera)
            public["status"] = statuses.get(str(camera["id"]), {"state": "disabled", "detail": ""})
            result.append(public)
        return result

    @app.post("/api/cameras", status_code=201)
    async def add_camera(payload: CameraPayload, _: None = Depends(require_csrf)) -> dict:
        cameras = store.load_cameras()
        camera = _validated_camera(payload)
        cameras.append(camera)
        store.save_cameras(cameras)
        manager.sync(cameras)
        return store.public_camera(camera)

    @app.put("/api/cameras/{camera_id}")
    async def update_camera(camera_id: str, payload: CameraPayload, _: None = Depends(require_csrf)) -> dict:
        cameras = store.load_cameras()
        index = next((i for i, camera in enumerate(cameras) if str(camera["id"]) == camera_id), None)
        if index is None:
            raise HTTPException(status_code=404, detail="Camera not found")
        camera = _validated_camera(payload, cameras[index])
        cameras[index] = camera
        store.save_cameras(cameras)
        manager.sync(cameras)
        return store.public_camera(camera)

    @app.delete("/api/cameras/{camera_id}", status_code=204)
    async def delete_camera(camera_id: str, _: None = Depends(require_csrf)) -> None:
        cameras = store.load_cameras()
        remaining = [camera for camera in cameras if str(camera["id"]) != camera_id]
        if len(remaining) == len(cameras):
            raise HTTPException(status_code=404, detail="Camera not found")
        store.save_cameras(remaining)
        manager.sync(remaining)

    @app.get("/api/detect-usb")
    async def detect(_: None = Depends(require_auth)) -> list[dict[str, str]]:
        return await run_in_threadpool(detect_usb_cameras)

    @app.get("/api/cameras/{camera_id}/stream")
    async def stream_camera(camera_id: str, _: None = Depends(require_auth)):
        cameras = store.load_cameras()
        if not any(str(camera["id"]) == camera_id and camera.get("enabled", True) for camera in cameras):
            raise HTTPException(status_code=404, detail="Camera not found or disabled")
        try:
            frames = manager.stream(camera_id, cameras)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Camera not found") from exc
        return StreamingResponse(
            frames,
            media_type="multipart/x-mixed-replace; boundary=frame",
            headers={"Cache-Control": "no-store, no-cache, must-revalidate", "X-Accel-Buffering": "no"},
        )

    return app
