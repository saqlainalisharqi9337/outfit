from app.tshirt_gate import CLASS_ORDER, lock_tshirt
from conftest import make_image


def test_tshirt_gate_classes_are_binary_tshirt_vs_other():
    assert CLASS_ORDER == ("t-shirt", "other")


def test_lock_tshirt_payload_is_upperwear_tshirt():
    result = lock_tshirt(make_image())
    if result is None:
        return
    assert result["category"] == "upperwear"
    assert result["subcategory"] == "t-shirt"
    assert result["source"] == "tshirt_gate"
