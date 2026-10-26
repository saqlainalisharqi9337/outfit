from app.fashionpedia_map import HINT_FROM_FASHIONPEDIA, hint_leaf


def test_fashionpedia_dress_and_jumpsuit_map_to_one_piece():
    assert hint_leaf("dress") == "dress"
    assert hint_leaf("jumpsuit") == "dress"


def test_fashionpedia_shorts_and_skirt_stay_distinct():
    assert hint_leaf("shorts") == "shorts"
    assert hint_leaf("skirt") == "skirt"
    assert hint_leaf("shorts") != hint_leaf("skirt")


def test_fashionpedia_accessories_and_shoes_map():
    assert hint_leaf("hat") == "hat"
    assert hint_leaf("belt") == "belt"
    assert hint_leaf("watch") == "watch"
    assert hint_leaf("shoe") == "shoes"


def test_fashionpedia_hints_do_not_rewrite_pants():
    assert "pants" not in HINT_FROM_FASHIONPEDIA
    assert hint_leaf("pants") is None
