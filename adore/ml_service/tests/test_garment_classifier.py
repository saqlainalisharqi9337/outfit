from app.garment_classifier import CONFUSED_LABELS, should_override


def test_should_override_covers_confused_upperwear_only():
    assert should_override("shirt") is True
    assert should_override("hoodie") is True
    assert should_override("top") is True
    assert should_override("unknown") is True
    assert should_override("dress") is False
    assert should_override("trousers") is False
    assert "dress" not in CONFUSED_LABELS
