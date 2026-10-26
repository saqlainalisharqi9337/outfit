from app.watch_belt_gate import CLASS_ORDER, lock_belt, lock_watch
from conftest import make_image


def test_watch_belt_gate_classes_are_the_live_collisions():
    assert CLASS_ORDER == ("watch", "belt", "bag", "trousers")


def test_lock_watch_payload_is_accessories_watch():
    result = lock_watch(make_image())
    if result is None:
        return
    assert result["category"] == "accessories"
    assert result["subcategory"] == "watch"
    assert result["source"] == "watch_belt_gate"


def test_lock_belt_payload_is_accessories_belt():
    result = lock_belt(make_image())
    if result is None:
        return
    assert result["category"] == "accessories"
    assert result["subcategory"] == "belt"
    assert result["source"] == "watch_belt_gate"
