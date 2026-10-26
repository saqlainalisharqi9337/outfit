from app.jacket_gate import CLASS_ORDER, lock_jacket
from conftest import make_image


def test_jacket_gate_classes_are_binary_jacket_vs_other():
    assert CLASS_ORDER == ("jacket", "other")


def test_lock_jacket_payload_is_upperwear_jacket():
    result = lock_jacket(make_image())
    if result is None:
        return
    assert result["category"] == "upperwear"
    assert result["subcategory"] == "jacket"
    assert result["source"] == "jacket_gate"
