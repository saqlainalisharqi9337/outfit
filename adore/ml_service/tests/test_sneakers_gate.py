from app.sneakers_gate import CLASS_ORDER, lock_sneakers
from conftest import make_image


def test_sneakers_gate_classes_are_binary_sneakers_vs_other():
    assert CLASS_ORDER == ("sneakers", "other")


def test_lock_sneakers_payload_is_footwear_sneakers():
    result = lock_sneakers(make_image())
    if result is None:
        return
    assert result["category"] == "footwear"
    assert result["subcategory"] == "sneakers"
    assert result["source"] == "sneakers_gate"
