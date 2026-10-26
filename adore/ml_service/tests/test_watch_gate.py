from app.watch_gate import CLASS_ORDER, lock_watch
from conftest import make_image


def test_watch_gate_classes_are_the_live_collisions():
    assert CLASS_ORDER == ("watch", "bag", "trousers")


def test_lock_watch_payload_is_accessories_watch():
    result = lock_watch(make_image())
    if result is None:
        return
    assert result["category"] == "accessories"
    assert result["subcategory"] == "watch"
    assert result["source"] == "watch_gate"
