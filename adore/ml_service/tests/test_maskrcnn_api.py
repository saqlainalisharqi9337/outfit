"""Mask R-CNN is the clothing detector when enabled. The checkpoint is not loaded."""

from app import config, maskrcnn_detector
from app.outfit_parser import parse_outfit
from conftest import make_image


def test_parse_outfit_uses_maskrcnn_items(monkeypatch):
    monkeypatch.setenv("ADORE_MASKRCNN_ENABLED", "1")
    config.reset_settings()

    def fake_detect(_image):
        return [
            {
                "class": "jacket",
                "category": "upperwear",
                "subcategory": "jacket",
                "confidence": 0.91,
                "bbox": [0.10, 0.12, 0.62, 0.70],
                "source": "maskrcnn",
                "region": "maskrcnn",
                "usedFallback": False,
            },
            {
                "class": "trousers",
                "category": "lowerwear",
                "subcategory": "trousers",
                "confidence": 0.74,
                "bbox": [0.18, 0.55, 0.70, 0.95],
                "source": "maskrcnn",
                "region": "maskrcnn",
                "usedFallback": False,
            },
        ]

    monkeypatch.setattr("app.maskrcnn_detector.detect_items", fake_detect)
    result = parse_outfit(make_image())
    assert result["detectionStrategy"] == "maskrcnn"
    assert result["source"] == "maskrcnn"
    assert result["subcategory"] == "jacket"
    assert result["category"] == "upperwear"
    assert result["usedFallback"] is False
    labels = [row["subcategory"] for row in result["detected"]]
    assert labels == ["jacket", "trousers"]
    assert result["detected"][0]["bbox"][0] == 0.10


def test_maskrcnn_disabled_returns_none():
    assert maskrcnn_detector.detect_items(make_image()) is None


def test_live_default_uses_mobilenet_not_maskrcnn(monkeypatch):
    monkeypatch.delenv("ADORE_MASKRCNN_ENABLED", raising=False)
    config.reset_settings()
    assert config.get_settings().maskrcnn_enabled is False
    assert maskrcnn_detector.detect_items(make_image()) is None
