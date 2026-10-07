import time

import numpy as np

from app.cameras import CameraManager, CameraWorker, source_for_capture


class FakeCapture:
    def __init__(self, frames, opened=True):
        self.frames = list(frames)
        self.opened = opened
        self.released = False

    def isOpened(self):
        return self.opened

    def read(self):
        if not self.frames:
            return False, None
        return self.frames.pop(0)

    def release(self):
        self.released = True


def wait_for(predicate, timeout=3):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.03)
    return False


def test_network_credentials_are_injected_only_for_capture():
    source = source_for_capture({"source_type": "rtsp", "source": "rtsp://cam.local/live", "username": "a@b", "password": "p:q"})
    assert source == "rtsp://a%40b:p%3Aq@cam.local/live"


def test_disconnected_camera_reconnects_and_publishes_frame():
    frame = np.full((24, 32, 3), 125, dtype=np.uint8)
    captures = [FakeCapture([], opened=False), FakeCapture([(True, frame)] * 20)]

    def factory(_source, _type):
        return captures.pop(0) if captures else FakeCapture([(True, frame)] * 20)

    worker = CameraWorker({"id": "one", "name": "Test", "source_type": "usb", "source": "0", "enabled": True}, factory)
    worker.start()
    try:
        assert wait_for(lambda: worker.status()["reconnects"] >= 1)
        assert wait_for(lambda: worker._frame is not None)
    finally:
        worker.stop()


def test_two_camera_workers_run_independently():
    frame = np.zeros((20, 20, 3), dtype=np.uint8)

    def factory(_source, _type):
        return FakeCapture([(True, frame)] * 100)

    cameras = [
        {"id": "one", "name": "One", "source_type": "usb", "source": "0", "enabled": True},
        {"id": "two", "name": "Two", "source_type": "usb", "source": "1", "enabled": True},
    ]
    manager = CameraManager(factory)
    manager.sync(cameras)
    streams = [manager.stream(camera["id"], cameras) for camera in cameras]
    try:
        first = [next(stream) for stream in streams]
        assert all(chunk.startswith(b"--frame") for chunk in first)
        assert set(manager.statuses()) == {"one", "two"}
    finally:
        manager.shutdown()
