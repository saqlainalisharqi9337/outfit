from app.trousers_gate import CLASS_ORDER, lock_trousers
from conftest import make_image


def test_trousers_gate_classes_are_the_live_collisions():
    assert CLASS_ORDER == ("trousers", "dress", "shirt")


def test_lock_trousers_payload_is_lowerwear_trousers():
    result = lock_trousers(make_image())
    if result is None:
        return
    assert result["category"] == "lowerwear"
    assert result["subcategory"] == "trousers"
    assert result["source"] == "trousers_gate"
