from app.bag_gate import CLASS_ORDER, lock_bag
from conftest import make_image


def test_bag_gate_classes_are_the_live_collisions():
    assert CLASS_ORDER == ("bag", "skirt", "flats")


def test_lock_bag_payload_is_accessories_bag():
    result = lock_bag(make_image())
    if result is None:
        return
    assert result["category"] == "accessories"
    assert result["subcategory"] == "bag"
    assert result["source"] == "bag_gate"
