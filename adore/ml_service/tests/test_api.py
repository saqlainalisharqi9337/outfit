from fastapi.testclient import TestClient

from app.main import app
from conftest import png_bytes


def test_health_live_does_not_require_models():
    client = TestClient(app)
    response = client.get("/health/live")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["status"] == "alive"


def test_health_reports_detector_and_classifiers(detector_disabled):
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "detector" in body
    assert "classifiers" in body
    assert "YOLOv8" in body["pipeline"]
    assert "colour" in body["pipeline"]
    assert body["detector"]["clothingClassesTrained"] == []
    assert "ready" in body
    assert "gate" in body


def test_detect_rejects_invalid_image(detector_disabled):
    client = TestClient(app)
    response = client.post(
        "/detect",
        files={"file": ("bad.txt", b"not-an-image", "text/plain")},
    )
    assert response.status_code == 400


def test_detect_returns_schema_when_disabled(detector_disabled):
    client = TestClient(app)
    response = client.post(
        "/detect",
        files={"file": ("x.png", png_bytes(), "image/png")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["detectorAvailable"] is False
    assert body["strategy"] == "fallback"
    assert "detections" in body
    assert "regions" in body
    assert "thresholds" in body


def test_analyze_clothing_rejects_empty_upload(detector_disabled):
    client = TestClient(app)
    response = client.post(
        "/analyze-clothing",
        files={"file": ("empty.png", b"", "image/png")},
    )
    assert response.status_code == 400


def test_analyze_clothing_still_accepts_png(detector_disabled):
    client = TestClient(app)
    response = client.post(
        "/analyze-clothing",
        files={"file": ("x.png", png_bytes(), "image/png")},
    )
    assert response.status_code == 200
    body = response.json()
    assert "subcategory" in body
    assert "category" in body
    assert "color" in body
    assert "primaryColor" in body
    assert "colorDistribution" in body
    assert "isMulticolor" in body


def test_debug_colors_returns_panels(detector_disabled):
    client = TestClient(app)
    response = client.post(
        "/debug-colors",
        files={"file": ("x.png", png_bytes(), "image/png")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "primaryColor" in body
    assert "collagePngBase64" in body


def test_teach_clothing_saves_labeled_photo(tmp_path, monkeypatch, detector_disabled):
    monkeypatch.setattr("app.teach.USER_DIR", tmp_path / "user_labeled")
    client = TestClient(app)
    response = client.post(
        "/teach-clothing",
        files={"file": ("x.png", png_bytes(), "image/png")},
        data={"label": "pent"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["class"] == "lowerwear_trousers"
    assert body["saved"] == 1
    assert (tmp_path / "user_labeled" / "lowerwear_trousers").is_dir()


def test_teach_clothing_rejects_unknown_label(detector_disabled):
    client = TestClient(app)
    response = client.post(
        "/teach-clothing",
        files={"file": ("x.png", png_bytes(), "image/png")},
        data={"label": "spaceship"},
    )
    assert response.status_code == 400
