"""Regression: lowerwear + sneaker paths must stay unchanged by router fixes.

These tests lock the contracts that the confusion-fix work must not break:
- trousers/shorts/skirt taxonomy and lowerwear specialist API
- sneakers remain a first-class footwear refine target
"""

from __future__ import annotations

from app.clothing_taxonomy import FOOTWEAR, apply_family_constraints
from app import footwear_classifier
from app import lowerwear_classifier


def test_sneakers_still_in_footwear_set():
    assert "sneakers" in FOOTWEAR
    assert "heels" in FOOTWEAR
    assert "sandals" in FOOTWEAR


def test_sneakers_should_override_unchanged():
    """Sneaker refine path must remain enabled (footwear4 has sneakers)."""
    footwear_classifier._ensure_loaded()
    assert footwear_classifier.should_override("sneakers") is True
    assert footwear_classifier.should_override("shoes") is True
    # Sandals stay ImageNet-passthrough (not destroyed by sneakers logic).
    assert footwear_classifier.should_override("sandals") is False


def test_lowerwear_specialist_api_unchanged():
    """Do not retrain or rewrite lowerwear — only assert the public contract."""
    status = lowerwear_classifier.status()
    assert "classes" in status
    classes = set(status.get("classes") or [])
    # Specialist must still expose trousers/shorts/skirt (names may vary slightly).
    assert classes & {"trousers", "shorts", "skirt", "pants", "jeans"}


def test_trousers_taxonomy_still_beats_hat():
    label, conf, uncertain, _msg = apply_family_constraints(
        [("trousers", 0.40), ("hat", 0.35), ("skirt", 0.08)]
    )
    assert label == "trousers"
    assert uncertain is False
    assert conf >= 0.40


def test_shorts_taxonomy_still_valid():
    label, conf, uncertain, _msg = apply_family_constraints(
        [("shorts", 0.42), ("hat", 0.10), ("bag", 0.05)]
    )
    assert label == "shorts"
    assert uncertain is False


def test_skirt_taxonomy_still_valid():
    label, conf, uncertain, _msg = apply_family_constraints(
        [("skirt", 0.45), ("dress", 0.12), ("hat", 0.05)]
    )
    assert label == "skirt"
    assert uncertain is False


def test_sneakers_not_rewritten_to_weak_hat():
    label, conf, uncertain, _msg = apply_family_constraints(
        [("sneakers", 0.40), ("hat", 0.12), ("bag", 0.05)]
    )
    assert label == "sneakers"
    assert uncertain is False


def test_human_review_flag_on_unknown():
    from app.clothing_classifier import _attach_human_review

    flagged = _attach_human_review(
        {
            "subcategory": "unknown",
            "confidence": 0.10,
            "usedFallback": True,
            "category": "accessories",
        }
    )
    assert flagged["needsHumanReview"] is True
    assert flagged["humanReviewThreshold"] >= 0.40


def test_human_review_not_required_when_confident():
    from app.clothing_classifier import _attach_human_review
    from app.config import reset_settings

    reset_settings()
    flagged = _attach_human_review(
        {
            "subcategory": "sneakers",
            "confidence": 0.88,
            "usedFallback": False,
            "category": "footwear",
        }
    )
    assert flagged["needsHumanReview"] is False
