from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_camera_cards_offer_client_side_screenshot_and_recording():
    html = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
    javascript = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    server = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert 'class="snapshot"' in html
    assert 'class="record"' in html
    assert "canvas.captureStream(15)" in javascript
    assert "new MediaRecorder" in javascript
    assert "link.download = filename" in javascript
    assert "/record" not in server


def test_camera_dialog_offers_saved_video_adjustments():
    html = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
    javascript = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    for control in ("camera-resolution", "camera-fps", "camera-rotation", "camera-flip"):
        assert f'id="{control}"' in html
    assert 'value="90">90° right' in html
    assert 'value="270">90° left' in html
    assert 'value="180">180° upside down' in html
    assert "target_width: width" in javascript
    assert "target_fps: Number" in javascript
