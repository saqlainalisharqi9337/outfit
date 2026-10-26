from app.clothing_taxonomy import apply_family_constraints, extra_items
from app.detection_schema import Detection, normalize_bbox
from app.outfit_parser import parse_outfit
from app.region_proposals import body_regions, from_person_box
from conftest import make_image


def test_bbox_rejects_malformed_and_clamps():
    assert normalize_bbox(None) is None
    assert normalize_bbox([0.1, 0.2]) is None
    assert normalize_bbox(["a", 0, 1, 1]) is None
    box = normalize_bbox([-0.2, 0.1, 1.4, 0.9])
    assert box == [0.0, 0.1, 1.0, 0.9]
    assert normalize_bbox([0.5, 0.5, 0.5, 0.8]) is None


def test_unknown_stays_unknown():
    label, _conf, uncertain, _msg = apply_family_constraints([])
    assert label == "unknown"
    assert uncertain is True


def test_weak_scores_do_not_invent_a_class():
    label, _conf, uncertain, _msg = apply_family_constraints(
        [("shirt", 0.11), ("dress", 0.10)]
    )
    assert label == "unknown"
    assert uncertain is True


def test_detection_to_item_keeps_flutter_keys():
    item = Detection(
        label="bag",
        confidence=0.91,
        category="accessories",
        source="yolo",
        bbox=[0.1, 0.2, 0.4, 0.6],
        region="detect_handbag",
        detector_label="handbag",
        detector_confidence=0.71,
        refined_label="bag",
        refined_confidence=0.91,
    ).to_item()
    assert item["subcategory"] == "bag"
    assert item["bbox"] == [0.1, 0.2, 0.4, 0.6]
    assert item["detectorLabel"] == "handbag"
    assert item["refinedLabel"] == "bag"


def test_person_bands_are_inside_the_person_box():
    person = [0.30, 0.10, 0.70, 0.90]
    bands = from_person_box(person)
    names = {name for name, _box, _allowed in bands}
    assert {"headwear", "upper", "lower", "feet"} <= names
    for name, box, _allowed in bands:
        if name.startswith("bag_"):
            continue
        x1, y1, x2, y2 = box
        assert x1 >= 0.0 and y1 >= 0.0 and x2 <= 1.0 and y2 <= 1.0
        assert x2 > x1 and y2 > y1


def test_no_person_uses_fallback_strategy():
    strategy, regions = body_regions(person=None, keypoints=None)
    assert strategy == "fallback"
    assert len(regions) >= 4


def test_person_strategy_is_preferred_over_fallback():
    strategy, regions = body_regions(person=[0.2, 0.05, 0.8, 0.95])
    assert strategy == "person"
    assert regions


def test_detector_unavailable_falls_back(detector_disabled):
    from app.object_detector import analyze, status

    result = analyze(make_image())
    assert result.available is False
    assert result.objects == []
    payload = status()
    assert payload["available"] is False
    assert payload["clothingClassesTrained"] == []


def test_fake_detector_returns_real_boxes(fake_detector):
    from app.object_detector import analyze

    fake_detector()
    result = analyze(make_image())
    assert result.available is True
    assert result.person is not None
    assert result.objects
    bag = result.objects[0]
    assert bag.detector_label == "handbag"
    assert bag.allowed == frozenset({"bag"})
    assert len(bag.bbox) == 4


def test_outfit_parser_fallback_does_not_crash(detector_disabled):
    payload = parse_outfit(make_image())
    assert "subcategory" in payload
    assert "isolatedProduct" in payload
    assert payload.get("detectionStrategy") == "fallback"


def test_extra_items_never_promote_unknown():
    extras = extra_items([("unknown", 0.9), ("shirt", 0.05)], "hat")
    assert all(row["subcategory"] != "unknown" for row in extras)


def test_weak_hat_does_not_rewrite_shirt():
    label, conf, uncertain, _msg = apply_family_constraints(
        [("shirt", 0.42), ("hat", 0.18), ("bag", 0.05)]
    )
    assert label == "shirt"
    assert uncertain is False
    assert conf >= 0.40


def test_hat_loses_to_competitive_shirt_row():
    label, conf, uncertain, _msg = apply_family_constraints(
        [("hat", 0.22), ("shirt", 0.21), ("t-shirt", 0.10)]
    )
    assert label == "shirt"
    assert uncertain is False


def test_trousers_are_never_rewritten_to_hat():
    label, conf, uncertain, _msg = apply_family_constraints(
        [("trousers", 0.40), ("hat", 0.35), ("skirt", 0.08)]
    )
    assert label == "trousers"
    assert uncertain is False


def test_dress_never_rewrites_to_shirt():
    label, conf, uncertain, _msg = apply_family_constraints(
        [("dress", 0.35), ("t-shirt", 0.18), ("hat", 0.05)]
    )
    assert label == "t-shirt"
    assert uncertain is False
    assert conf >= 0.18


def test_dress_never_rewrites_to_trousers():
    label, conf, uncertain, _msg = apply_family_constraints(
        [("dress", 0.40), ("trousers", 0.12)]
    )
    assert label == "trousers"
    assert uncertain is False


def test_heels_not_rewritten_to_weak_hat():
    label, conf, uncertain, _msg = apply_family_constraints(
        [("heels", 0.38), ("hat", 0.10), ("bag", 0.04)]
    )
    assert label == "heels"
    assert uncertain is False


def test_footwear_should_not_override_heels_without_heels_class():
    from app import footwear_classifier

    prev = (
        footwear_classifier._loaded,
        footwear_classifier._model,
        list(footwear_classifier._labels),
        footwear_classifier._error,
    )
    try:
        footwear_classifier._loaded = True
        footwear_classifier._model = object()
        footwear_classifier._labels = ["shoes", "flats", "sneakers"]
        footwear_classifier._error = ""
        assert footwear_classifier.should_override("heels") is False
        assert footwear_classifier.should_override("shoes") is True
        assert footwear_classifier.should_override("sandals") is False
    finally:
        (
            footwear_classifier._loaded,
            footwear_classifier._model,
            footwear_classifier._labels,
            footwear_classifier._error,
        ) = prev
        footwear_classifier._labels = list(prev[2])


def test_imagenet_pairs_keep_jeans_over_hat():
    from app.clothing_classifier import _from_imagenet_pairs

    result = _from_imagenet_pairs(
        [
            ("jean", 0.40),
            ("cowboy_hat", 0.12),
            ("running_shoe", 0.05),
        ]
    )
    assert result["subcategory"] == "jeans"
    assert result["category"] == "lowerwear"


def test_imagenet_pairs_keep_shirt_signal_over_weak_hat():
    from app.clothing_classifier import _from_imagenet_pairs

    result = _from_imagenet_pairs(
        [
            ("pajama", 0.28),
            ("cowboy_hat", 0.14),
            ("jersey", 0.10),
        ]
    )
    assert result["subcategory"] in {"shirt", "t-shirt"}
    assert result["category"] == "upperwear"


def test_empty_cream_crop_has_low_occupancy():
    from PIL import Image

    from app.clothing_taxonomy import crop_foreground_occupancy

    cream = Image.new("RGB", (200, 200), (245, 240, 230))
    assert crop_foreground_occupancy(cream) < 0.05


def test_merge_drops_bag_when_trousers_are_confident():
    from app.outfit_parser import _merge

    merged = _merge(
        [
            {
                "category": "lowerwear",
                "subcategory": "trousers",
                "confidence": 1.0,
                "bbox": [0.0, 0.0, 1.0, 1.0],
                "source": "full",
                "region": "full",
                "usedFallback": False,
            },
            {
                "category": "accessories",
                "subcategory": "bag",
                "confidence": 0.69,
                "bbox": [0.70, 0.26, 1.0, 0.78],
                "source": "bag_right",
                "region": "bag_right",
                "usedFallback": False,
            },
        ],
        closeup=True,
    )
    assert all(row["subcategory"] != "bag" for row in merged)
    assert merged[0]["subcategory"] == "trousers"


def test_merge_hat_beats_shorts_on_closeup():
    from app.outfit_parser import _merge

    merged = _merge(
        [
            {
                "category": "lowerwear",
                "subcategory": "shorts",
                "confidence": 0.81,
                "bbox": [0.0, 0.0, 1.0, 1.0],
                "source": "lowerwear",
                "region": "full",
                "usedFallback": False,
            },
            {
                "category": "accessories",
                "subcategory": "hat",
                "confidence": 0.55,
                "bbox": [0.0, 0.0, 1.0, 1.0],
                "source": "accessory",
                "region": "full",
                "usedFallback": False,
            },
        ],
        closeup=True,
    )
    assert merged[0]["subcategory"] == "hat"
    assert all(row["subcategory"] != "shorts" for row in merged)
