from app.lowerwear5 import CONFUSED_LABELS, should_override


def test_lowerwear5_should_override_covers_bottomwear_only():
    assert should_override("trousers") is True
    assert should_override("shorts") is True
    assert should_override("skirt") is True
    assert should_override("shalwar") is True
    assert should_override("leggings") is True
    assert should_override("shirt") is False
    assert should_override("dress") is False
    assert "dress" not in CONFUSED_LABELS
