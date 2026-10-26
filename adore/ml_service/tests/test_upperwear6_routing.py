"""The 6-class upperwear head must be returned instead of shirt/jacket gates."""

from app.clothing_classifier import _classify_clothing_core
from conftest import make_image


def test_hoodie_from_upperwear6_beats_jacket_gate(monkeypatch, detector_disabled):
    hoodie = {
        "category": "upperwear",
        "subcategory": "hoodie",
        "confidence": 0.62,
        "usedFallback": False,
        "source": "upperwear",
        "message": "Detected Hoodie (62%).",
        "displayName": "Hoodie",
        "items": [],
    }
    jacket = {
        "category": "upperwear",
        "subcategory": "jacket",
        "confidence": 0.88,
        "usedFallback": False,
        "source": "jacket_gate",
        "message": "Detected jacket.",
        "displayName": "Jacket",
        "items": [],
    }
    monkeypatch.setattr(
        "app.clothing_classifier._ensure_loaded", lambda: None
    )
    monkeypatch.setattr(
        "app.clothing_classifier._classify_imagenet",
        lambda _img: {
            "subcategory": "shirt",
            "confidence": 0.41,
            "items": [],
            "usedFallback": False,
        },
    )
    monkeypatch.setattr("app.clothing_classifier._classify_finetuned", lambda _img: None)
    monkeypatch.setattr("app.clothing_classifier._prefer_accessory", lambda inet, _ft: inet)
    monkeypatch.setattr(
        "app.object_detector.fashionpedia_item_hint", lambda _img: {}
    )
    monkeypatch.setattr("app.trousers_gate.lock_or_prefer_trousers", lambda *_a, **_k: None)
    monkeypatch.setattr("app.skirt_gate.lock_or_prefer_skirt", lambda *_a, **_k: None)
    monkeypatch.setattr("app.shirt_gate.lock_or_prefer_shirt", lambda *_a, **_k: None)
    monkeypatch.setattr("app.tshirt_gate.lock_or_prefer_tshirt", lambda *_a, **_k: None)
    monkeypatch.setattr("app.jacket_gate.lock_or_prefer_jacket", lambda *_a, **_k: jacket)
    monkeypatch.setattr("app.flats_gate.lock_or_prefer_flats", lambda *_a, **_k: None)
    monkeypatch.setattr("app.heels_gate.lock_or_prefer_heels", lambda *_a, **_k: None)
    monkeypatch.setattr("app.sneakers_gate.lock_or_prefer_sneakers", lambda *_a, **_k: None)
    monkeypatch.setattr("app.shoes_gate.lock_or_prefer_shoes", lambda *_a, **_k: None)
    monkeypatch.setattr("app.garment_classifier.classify_garment", lambda _img: hoodie)
    monkeypatch.setattr("app.garment_classifier.loaded_classes", lambda: ["hoodie"])
    monkeypatch.setattr("app.lowerwear5.classify_lowerwear5", lambda _img: None)

    out = _classify_clothing_core(make_image())
    assert out["subcategory"] == "hoodie"
    assert out["source"] == "upperwear"


def test_dress_from_upperwear6_beats_shirt_gate(monkeypatch, detector_disabled):
    dress = {
        "category": "dress",
        "subcategory": "dress",
        "confidence": 0.71,
        "usedFallback": False,
        "source": "upperwear",
        "message": "Detected Dress (71%).",
        "displayName": "Dress",
        "items": [],
    }
    shirt = {
        "category": "upperwear",
        "subcategory": "shirt",
        "confidence": 0.91,
        "usedFallback": False,
        "source": "shirt_gate",
        "message": "Detected shirt.",
        "displayName": "Shirt",
        "items": [],
    }
    monkeypatch.setattr("app.clothing_classifier._ensure_loaded", lambda: None)
    monkeypatch.setattr(
        "app.clothing_classifier._classify_imagenet",
        lambda _img: {
            "subcategory": "shirt",
            "confidence": 0.40,
            "items": [],
            "usedFallback": False,
        },
    )
    monkeypatch.setattr("app.clothing_classifier._classify_finetuned", lambda _img: None)
    monkeypatch.setattr("app.clothing_classifier._prefer_accessory", lambda inet, _ft: inet)
    monkeypatch.setattr("app.object_detector.fashionpedia_item_hint", lambda _img: {})
    monkeypatch.setattr("app.trousers_gate.lock_or_prefer_trousers", lambda *_a, **_k: None)
    monkeypatch.setattr("app.skirt_gate.lock_or_prefer_skirt", lambda *_a, **_k: None)
    monkeypatch.setattr("app.shirt_gate.lock_or_prefer_shirt", lambda *_a, **_k: shirt)
    monkeypatch.setattr("app.tshirt_gate.lock_or_prefer_tshirt", lambda *_a, **_k: None)
    monkeypatch.setattr("app.jacket_gate.lock_or_prefer_jacket", lambda *_a, **_k: None)
    monkeypatch.setattr("app.flats_gate.lock_or_prefer_flats", lambda *_a, **_k: None)
    monkeypatch.setattr("app.heels_gate.lock_or_prefer_heels", lambda *_a, **_k: None)
    monkeypatch.setattr("app.sneakers_gate.lock_or_prefer_sneakers", lambda *_a, **_k: None)
    monkeypatch.setattr("app.shoes_gate.lock_or_prefer_shoes", lambda *_a, **_k: None)
    monkeypatch.setattr("app.garment_classifier.classify_garment", lambda _img: dress)
    monkeypatch.setattr("app.lowerwear5.classify_lowerwear5", lambda _img: None)

    out = _classify_clothing_core(make_image())
    assert out["subcategory"] == "dress"
    assert out["category"] == "dress"
    assert out["source"] == "upperwear"
