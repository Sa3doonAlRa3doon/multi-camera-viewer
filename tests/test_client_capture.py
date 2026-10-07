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
