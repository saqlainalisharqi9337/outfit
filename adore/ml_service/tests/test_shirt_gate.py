from app.shirt_gate import CLASS_ORDER, lock_shirt
from conftest import make_image


def test_shirt_gate_is_binary_shirt_vs_other():
    assert CLASS_ORDER == ("shirt", "other")


def test_lock_shirt_payload_is_upperwear_shirt():
    result = lock_shirt(make_image())
    if result is None:
        return
    assert result["category"] == "upperwear"
    assert result["subcategory"] == "shirt"
    assert result["source"] == "shirt_gate"
