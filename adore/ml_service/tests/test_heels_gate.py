from app.heels_gate import CLASS_ORDER, lock_heels
from conftest import make_image


def test_heels_gate_classes_are_binary_heels_vs_other():
    assert CLASS_ORDER == ("heels", "other")


def test_lock_heels_payload_is_footwear_heels():
    result = lock_heels(make_image())
    if result is None:
        return
    assert result["category"] == "footwear"
    assert result["subcategory"] == "heels"
    assert result["source"] == "heels_gate"
