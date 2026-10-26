"""Smoke-test outfit recommendation pairing logic (no Google scrape).

Uses wardrobe items with correct categories — the same contract Flutter's
RecommendationService expects after ML labeling.
"""

from __future__ import annotations


def can_form_outfit(items: list[dict]) -> tuple[bool, str]:
    cats = {i["category"] for i in items}
    has_dress = "dress" in cats
    has_top = "upperwear" in cats
    has_bottom = "lowerwear" in cats
    has_shoes = "footwear" in cats
    if has_dress and has_shoes:
        return True, "dress+shoes"
    if has_top and has_bottom and has_shoes:
        return True, "top+bottom+shoes"
    missing = []
    if not has_dress and not (has_top and has_bottom):
        if not has_top:
            missing.append("upperwear")
        if not has_bottom:
            missing.append("lowerwear")
    if not has_shoes:
        missing.append("footwear")
    return False, "missing:" + ",".join(missing)


def test_complete_casual_wardrobe():
    wardrobe = [
        {"category": "upperwear", "subcategory": "t-shirt"},
        {"category": "lowerwear", "subcategory": "trousers"},
        {"category": "footwear", "subcategory": "sneakers"},
        {"category": "accessories", "subcategory": "bag"},
    ]
    ok, why = can_form_outfit(wardrobe)
    assert ok, why
    assert why == "top+bottom+shoes"


def test_dress_outfit():
    wardrobe = [
        {"category": "dress", "subcategory": "dress"},
        {"category": "footwear", "subcategory": "heels"},
    ]
    ok, why = can_form_outfit(wardrobe)
    assert ok, why


def test_incomplete_without_shoes():
    wardrobe = [
        {"category": "upperwear", "subcategory": "shirt"},
        {"category": "lowerwear", "subcategory": "skirt"},
    ]
    ok, why = can_form_outfit(wardrobe)
    assert not ok
    assert "footwear" in why


def test_mislabel_dress_breaks_top_bottom_outfit():
    """If a t-shirt is labeled dress, top+bottom pairing fails."""
    wardrobe = [
        {"category": "dress", "subcategory": "dress"},  # mislabeled t-shirt
        {"category": "lowerwear", "subcategory": "trousers"},
        {"category": "footwear", "subcategory": "sneakers"},
    ]
    # dress+shoes still forms an outfit, but wrong item type
    ok, why = can_form_outfit(wardrobe)
    assert ok and why == "dress+shoes"
    # Correct labeling should be top+bottom+shoes
    fixed = [
        {"category": "upperwear", "subcategory": "t-shirt"},
        {"category": "lowerwear", "subcategory": "trousers"},
        {"category": "footwear", "subcategory": "sneakers"},
    ]
    ok2, why2 = can_form_outfit(fixed)
    assert ok2 and why2 == "top+bottom+shoes"


if __name__ == "__main__":
    test_complete_casual_wardrobe()
    test_dress_outfit()
    test_incomplete_without_shoes()
    test_mislabel_dress_breaks_top_bottom_outfit()
    print("recommendation smoke tests OK")
