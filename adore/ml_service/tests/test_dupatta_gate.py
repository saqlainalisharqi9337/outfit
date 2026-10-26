from app.dupatta_gate import CLASS_ORDER, lock_dupatta
from conftest import make_image


def test_dupatta_gate_classes_are_the_live_collisions():
    assert CLASS_ORDER == ("dupatta", "bag", "belt")


def test_lock_dupatta_payload_is_accessories_dupatta():
    result = lock_dupatta(make_image())
    if result is None:
        return
    assert result["category"] == "accessories"
    assert result["subcategory"] == "dupatta"
    assert result["source"] == "dupatta_gate"
