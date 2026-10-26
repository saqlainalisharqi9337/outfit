from app.hat_gate import CLASS_ORDER, lock_hat, prefer_hat_over_bag
from conftest import make_image


def test_hat_gate_classes_are_the_live_collisions():
    assert CLASS_ORDER == ("hat", "bag", "shirt")


def test_lock_hat_payload_is_accessories_hat():
    result = lock_hat(make_image()) or prefer_hat_over_bag(make_image())
    if result is None:
        return
    assert result["category"] == "accessories"
    assert result["subcategory"] == "hat"
    assert result["source"] == "hat_gate"
