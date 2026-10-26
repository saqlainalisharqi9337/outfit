from app.fashionpedia_map import (
    ACCESSORY_FROM_FASHIONPEDIA,
    FASHIONPEDIA_NAMES,
    accessory_leaf,
    allowed_leaves,
    name_for_index,
)
from app.outfit_parser import _classify_crop
from conftest import make_image


def test_fashionpedia_ontology_has_accessories_deepfashion2_lacks():
    names = set(FASHIONPEDIA_NAMES)
    assert "bag, wallet" in names
    assert "hat" in names
    assert "glasses" in names
    assert "belt" in names
    assert "scarf" in names
    # DeepFashion2's 13 classes never included these.
    assert "short sleeve dress" not in names


def test_bag_and_hat_map_to_adore_leaves():
    assert accessory_leaf("bag, wallet") == "bag"
    assert accessory_leaf("hat") == "hat"
    assert accessory_leaf("glasses") == "sunglasses"
    assert accessory_leaf("scarf") == "scarf"
    assert accessory_leaf(24) == "bag"
    assert allowed_leaves("scarf") == frozenset({"scarf", "dupatta"})
    assert allowed_leaves("pants") == frozenset({"trousers"})


def test_index_14_is_hat():
    assert name_for_index(14) == "hat"
    assert name_for_index(13) == "glasses"


def test_accessory_crop_does_not_require_skirt_class():
    from app.accessory_classifier import TRUE_ACCESSORIES

    assert "skirt" not in TRUE_ACCESSORIES
    assert "shoes" not in TRUE_ACCESSORIES
    assert {"bag", "hat", "belt", "scarf", "dupatta", "hijab", "jewelry", "sunglasses"} <= TRUE_ACCESSORIES


def test_classify_crop_empty_allowed_falls_through(monkeypatch):
    called = {"n": 0}

    def fake_classify(_image):
        called["n"] += 1
        return {"subcategory": "shirt", "usedFallback": False, "confidence": 0.9}

    monkeypatch.setattr(
        "app.accessory_classifier.classify_accessory",
        lambda *_a, **_k: {"subcategory": "bag", "usedFallback": False, "confidence": 0.9},
    )
    out = _classify_crop(make_image(), frozenset({"shirt"}), fake_classify)
    assert out["subcategory"] == "shirt"
    assert called["n"] == 1
