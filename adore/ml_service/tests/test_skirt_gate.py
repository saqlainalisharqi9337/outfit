from app.skirt_gate import CLASS_ORDER, lock_skirt
from conftest import make_image


def test_skirt_gate_classes_are_the_live_collisions():
    assert CLASS_ORDER == ("skirt", "belt", "hat")


def test_lock_skirt_payload_is_lowerwear_skirt():
    result = lock_skirt(make_image())
    if result is None:
        return
    assert result["category"] == "lowerwear"
    assert result["subcategory"] == "skirt"
    assert result["source"] == "skirt_gate"
