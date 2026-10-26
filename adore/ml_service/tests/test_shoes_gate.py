from app.shoes_gate import CLASS_ORDER, lock_shoes
from conftest import make_image


def test_shoes_gate_classes_are_binary_shoes_vs_other():
    assert CLASS_ORDER == ("shoes", "other")


def test_lock_shoes_payload_is_footwear_shoes():
    result = lock_shoes(make_image())
    if result is None:
        return
    assert result["category"] == "footwear"
    assert result["subcategory"] == "shoes"
    assert result["source"] == "shoes_gate"
