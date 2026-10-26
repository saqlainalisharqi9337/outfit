from app.flats_gate import CLASS_ORDER, lock_flats
from conftest import make_image


def test_flats_gate_classes_are_binary_flats_vs_other():
    assert CLASS_ORDER == ("flats", "other")


def test_lock_flats_payload_is_footwear_flats():
    result = lock_flats(make_image())
    if result is None:
        return
    assert result["category"] == "footwear"
    assert result["subcategory"] == "flats"
    assert result["source"] == "flats_gate"
