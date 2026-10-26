from app.fashionpedia_map import outfit20_id
from app.outfit20_taxonomy import OUTFIT20_CLASSES, from_fashionpedia, resolve_label


def test_nineteen_listed_outfit_classes():
    assert len(OUTFIT20_CLASSES) == 19


def test_fashionpedia_garments_are_not_dropped():
    assert from_fashionpedia("dress") == "one_piece_dress"
    assert from_fashionpedia("pants") == "lowerwear_trousers"
    assert from_fashionpedia("bag, wallet") == "accessories_bag"
    assert from_fashionpedia("skirt") == "lowerwear_skirt"
    assert from_fashionpedia("shoe") == "footwear_shoes"
    assert from_fashionpedia("sleeve") is None


def test_outfit20_id_helper():
    assert outfit20_id("jacket") == "upperwear_jacket"
    assert outfit20_id("top, t-shirt, sweatshirt") == "upperwear_tshirt"


def test_resolve_label_accepts_everyday_names():
    assert resolve_label("pent") == "lowerwear_trousers"
    assert resolve_label("pants") == "lowerwear_trousers"
    assert resolve_label("tshirt") == "upperwear_tshirt"
    assert resolve_label("t-shirt") == "upperwear_tshirt"
    assert resolve_label("upperwear_tshirt") == "upperwear_tshirt"
    assert resolve_label("not-a-garment") is None
