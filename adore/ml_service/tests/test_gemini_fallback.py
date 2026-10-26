"""Gemini is used only when the local clothing result is unsure."""

from app.gemini_clothing import _merge, _parse_label, low_confidence


def test_confident_local_result_is_kept():
    assert low_confidence({"subcategory": "shirt", "confidence": 0.8}) is False


def test_unknown_or_weak_result_asks_gemini():
    assert low_confidence({"subcategory": "unknown", "confidence": 0.9, "usedFallback": True})
    assert low_confidence({"subcategory": "shirt", "confidence": 0.2}) is True


def test_parse_rejects_labels_outside_the_wardrobe_list():
    assert _parse_label('{"subcategory":"spaceship","confidence":0.9}') is None
    parsed = _parse_label('{"subcategory":"jacket","color":"navy","confidence":0.81}')
    assert parsed is not None
    assert parsed["subcategory"] == "jacket"
    assert parsed["category"] == "upperwear"


def test_merge_keeps_the_api_shape():
    merged = _merge(
        {"subcategory": "unknown", "confidence": 0.1, "usedFallback": True, "color": "blue"},
        {"subcategory": "dress", "category": "dress", "confidence": "0.7700", "color": "red"},
    )
    assert merged["source"] == "gemini"
    assert merged["subcategory"] == "dress"
    assert merged["usedFallback"] is False
    assert merged["color"] == "blue"
    assert merged["detected"][0]["subcategory"] == "dress"
