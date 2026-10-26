"""Detect multiple garments in one photo, then classify each crop.

MobileNetV2 is a classifier: one crop -> one label. This module supplies the
missing detect step. Boxes come from a pretrained COCO detector where it can
help, and from region proposals where it cannot -- COCO has no clothing
classes, so no garment label originates here. See DETECTION_LIMITATIONS.md.

Pipeline:
  full image classify
  -> pretrained YOLO: person box + carried-bag boxes
  -> garment bands from pose keypoints, else the person box, else the frame
  -> classify each crop with the existing specialists
  -> color on that crop
  -> merge unique items with normalized bounding boxes

The whole detector stage is optional. With no weights installed every step
below falls back to the original frame-relative regions.
"""

from __future__ import annotations

from typing import Any

from PIL import Image

from . import accessory_classifier
from . import bag_gate
from . import hat_gate
from . import watch_belt_gate
from . import watch_gate
from . import dupatta_gate
from . import trousers_gate
from . import skirt_gate
from . import shirt_gate
from . import tshirt_gate
from . import jacket_gate
from . import flats_gate
from . import heels_gate
from . import sneakers_gate
from . import shoes_gate
from . import maskrcnn_detector
from . import object_detector
from . import outfit20_detector
from . import region_proposals
from .clothing_taxonomy import (
    crop_foreground_occupancy,
    family_of,
    is_closeup_item_frame,
    is_hanging_body_garment,
)
from .color_analysis import analyze_garment_colors
from .config import get_settings
from .detection_schema import Proposal, normalize_bbox

# Roles stop a shoe crop from becoming trousers. The canonical list now lives
# in region_proposals so the frame fallback and the person-anchored bands
# cannot drift apart; this alias keeps the old module-level name working.
REGIONS = region_proposals.FALLBACK_REGIONS


def parse_outfit(image: Image.Image) -> dict[str, Any]:
    from .clothing_classifier import classify_clothing

    settings = get_settings()
    rgb = image.convert("RGB")
    if settings.maskrcnn_enabled:
        mask_items = maskrcnn_detector.detect_items(rgb)
        if mask_items is not None:
            return _outfit_from_maskrcnn(rgb, mask_items)
    detection = object_detector.analyze(rgb)
    primary = classify_clothing(rgb)
    garment_box = detection.person
    color_info = analyze_garment_colors(rgb, bbox=garment_box).to_api()
    color, secondary = color_info.get("color"), color_info.get("secondaryColor")
    primary_item = _as_item(
        primary,
        color=color,
        secondary=secondary,
        bbox=[0.0, 0.0, 1.0, 1.0] if garment_box is None else list(garment_box),
        region="full",
        extra=color_info,
    )
    found: list[dict[str, Any]] = []
    if primary_item is not None:
        found.append(primary_item)

    # Existing Fashionpedia YOLO (or the improved 20-class fine-tune) emits
    # one box per visible garment. Do not collapse this to a single label.
    outfit_items = outfit20_detector.refine_footwear_and_wraps(
        rgb, outfit20_detector.detect_items(rgb)
    )
    for row in outfit_items:
        box = list(row.get("bbox") or [0.0, 0.0, 1.0, 1.0])
        crop_colors = analyze_garment_colors(rgb, bbox=box).to_api()
        item = _as_item(
            row,
            color=crop_colors.get("color"),
            secondary=crop_colors.get("secondaryColor"),
            bbox=box,
            region=str(row.get("region") or "outfit20"),
            extra=crop_colors,
        )
        if item is not None:
            item["class"] = row.get("class")
            found.append(item)

    closeup = is_closeup_item_frame(rgb)
    # Tall hanging jeans/pants fill the frame like an outfit, but there is
    # no person — side bag bands would classify empty cream as a bag.
    single_garment = (
        closeup
        or is_hanging_body_garment(rgb)
        or detection.person is None
    )
    extras = primary.get("items") or []
    primary_label = primary.get("subcategory") or "unknown"
    primary_is_pants = primary_label in {"trousers", "jeans", "shorts", "skirt"}
    for extra in extras:
        extra_label = extra.get("subcategory") if isinstance(extra, dict) else None
        # One object on a table is not a hat+skirt outfit.
        if closeup and extra_label in {"skirt", "shorts", "trousers", "jeans"}:
            if primary_label == "hat":
                continue
        item = _as_item(extra, bbox=None, region="imagenet")
        if item is not None:
            found.append(item)

    if not outfit_items:
        for proposal in detection.objects:
            # Do not attach a YOLO bag to a clear pants/jeans product shot.
            if (
                primary_is_pants
                and float(primary.get("confidence") or 0) >= 0.45
                and proposal.allowed == frozenset({"bag"})
            ):
                continue
            item = _classify_proposal(rgb, proposal, classify_clothing)
            if item is not None:
                found.append(item)

    strategy, regions = region_proposals.body_regions(
        person=detection.person,
        keypoints=detection.keypoints,
    )
    if _should_scan_regions(rgb, primary, person=detection.person) and len(outfit_items) < 2:
        primary_is_dress = (primary.get("subcategory") or "") in {
            "dress",
            "gown",
            "modest dress",
        }
        primary_is_hat = (primary.get("subcategory") or "") == "hat"
        primary_is_bag = (primary.get("subcategory") or "") == "bag"
        primary_is_strap = (primary.get("subcategory") or "") in {
            "belt",
            "watch",
            "sunglasses",
        }
        bag_regions = {"bag_left", "bag_right", "bag_front"}
        for region, box, allowed in regions:
            if primary_is_dress and region == "lower":
                continue
            # Portrait phone photos of a cap are tall, but they are not outfits.
            if (
                primary_is_hat or is_closeup_item_frame(rgb) or single_garment
            ) and region in {"upper", "lower"}:
                continue
            # Empty side bands on a pants product shot invent bags.
            if region in bag_regions and (
                primary_is_pants
                or primary_is_hat
                or single_garment
                or detection.person is None
            ):
                continue
            if primary_is_bag and region in {"upper", "lower", "bag_front"}:
                continue
            if primary_is_strap and region in {"upper", "lower"}:
                continue
            if region == "bag_front" and not (
                primary_is_dress or primary.get("subcategory") in {"unknown", "hat"}
            ):
                continue
            crop = _crop(rgb, box)
            if crop is None:
                continue
            if "bag" in allowed and crop_foreground_occupancy(crop) < 0.08:
                continue
            result = _classify_crop(crop, allowed, classify_clothing)
            label = result.get("subcategory") or "unknown"
            if result.get("usedFallback") or label == "unknown":
                continue
            if label not in allowed:
                continue
            if float(result.get("confidence") or 0) < settings.classifier_min_confidence:
                continue
            crop_colors = analyze_garment_colors(crop).to_api()
            item = _as_item(
                result,
                color=crop_colors.get("color"),
                secondary=crop_colors.get("secondaryColor"),
                bbox=list(box),
                region=region,
                extra=crop_colors,
            )
            if item is not None:
                found.append(item)

    if len(outfit_items) >= 2:
        found = [
            row
            for row in found
            if row.get("region") not in {"full", "imagenet"}
        ]
    merged = _merge(found, closeup=closeup or single_garment)
    if not merged:
        return {
            **primary,
            **color_info,
            "color": color,
            "secondaryColor": secondary,
            "items": [],
            "detected": [],
            "detections": [],
            "isolatedProduct": closeup,
            "detectionStrategy": strategy,
            "personBox": detection.person,
            "outfit20": outfit20_detector.status(),
        }

    lead = merged[0]
    others = merged[1:]
    names = [
        f"{row['subcategory']} ({row['confidence'] * 100:.0f}%)" for row in merged
    ]
    if primary.get("subcategory") == lead["subcategory"]:
        message = primary.get("message") or f"Detected {lead['subcategory']}."
    else:
        message = f"Detected {lead['subcategory']}."
    if len(merged) > 1:
        message = (
            f"Detected {len(merged)} items: {', '.join(names)}. "
            "Tap one to save it to your wardrobe."
        )
    detections = [
        {
            "class": row.get("class")
            or f"{row.get('category')}_{str(row.get('subcategory') or '').replace('-', '').replace(' ', '_')}",
            "category": row.get("category"),
            "subcategory": row.get("subcategory"),
            "confidence": round(float(row.get("confidence") or 0), 4),
            "bbox": row.get("bbox"),
            "source": row.get("source"),
            "color": row.get("color"),
            "secondaryColor": row.get("secondaryColor"),
            "primaryColor": row.get("primaryColor") or row.get("color"),
            "secondaryColors": row.get("secondaryColors") or [],
            "accentColors": row.get("accentColors") or [],
            "colorDistribution": row.get("colorDistribution") or {},
            "pattern": row.get("pattern") or "solid",
            "isMulticolor": bool(row.get("isMulticolor")),
        }
        for row in merged
    ]
    return {
        **primary,
        "category": lead["category"],
        "subcategory": lead["subcategory"],
        "source": lead.get("source") or primary.get("source"),
        "confidence": lead["confidence"],
        "displayName": lead["subcategory"],
        "color": lead.get("color") or color,
        "secondaryColor": lead.get("secondaryColor") or secondary,
        "primaryColor": lead.get("primaryColor") or lead.get("color") or color,
        "secondaryColors": lead.get("secondaryColors") or (
            [lead["secondaryColor"]] if lead.get("secondaryColor") else []
        ),
        "accentColors": lead.get("accentColors") or [],
        "colorDistribution": lead.get("colorDistribution") or {},
        "pattern": lead.get("pattern") or "solid",
        "patternType": lead.get("patternType") or "solid",
        "isMulticolor": bool(lead.get("isMulticolor")),
        "colorClusters": lead.get("colorClusters") or [],
        "message": message,
        "items": others,
        "detected": merged,
        "detections": detections,
        "isolatedProduct": closeup,
        "detectionStrategy": strategy,
        "personBox": detection.person,
        "outfit20": outfit20_detector.status(),
    }


def _outfit_from_maskrcnn(
    image: Image.Image, rows: list[dict[str, Any]]
) -> dict[str, Any]:
    """Build the /analyze-clothing payload from Mask R-CNN boxes only."""
    found: list[dict[str, Any]] = []
    for row in rows:
        box = list(row.get("bbox") or [0.0, 0.0, 1.0, 1.0])
        crop_colors = analyze_garment_colors(image, bbox=box).to_api()
        item = _as_item(
            row,
            color=crop_colors.get("color"),
            secondary=crop_colors.get("secondaryColor"),
            bbox=box,
            region="maskrcnn",
            extra=crop_colors,
        )
        if item is None:
            continue
        item["class"] = row.get("class") or row.get("subcategory")
        item["source"] = "maskrcnn"
        found.append(item)
    merged = _merge(found)
    merged.sort(key=lambda row: -float(row.get("confidence") or 0))
    if not merged:
        return {
            "category": "upperwear",
            "subcategory": "unknown",
            "confidence": 0.0,
            "usedFallback": True,
            "source": "maskrcnn",
            "message": "No clothing detected.",
            "color": None,
            "secondaryColor": None,
            "items": [],
            "detected": [],
            "detections": [],
            "isolatedProduct": False,
            "detectionStrategy": "maskrcnn",
            "personBox": None,
            "maskrcnn": maskrcnn_detector.status(),
        }
    lead = merged[0]
    others = merged[1:]
    names = [
        f"{row['subcategory']} ({float(row['confidence']) * 100:.0f}%)"
        for row in merged
    ]
    message = f"Detected {lead['subcategory']}."
    if len(merged) > 1:
        message = (
            f"Detected {len(merged)} items: {', '.join(names)}. "
            "Tap one to save it to your wardrobe."
        )
    detections = [
        {
            "class": row.get("class") or row.get("subcategory"),
            "category": row.get("category"),
            "subcategory": row.get("subcategory"),
            "confidence": round(float(row.get("confidence") or 0), 4),
            "bbox": row.get("bbox"),
            "source": "maskrcnn",
            "color": row.get("color"),
            "secondaryColor": row.get("secondaryColor"),
            "primaryColor": row.get("primaryColor") or row.get("color"),
            "secondaryColors": row.get("secondaryColors") or [],
            "accentColors": row.get("accentColors") or [],
            "colorDistribution": row.get("colorDistribution") or {},
            "pattern": row.get("pattern") or "solid",
            "isMulticolor": bool(row.get("isMulticolor")),
        }
        for row in merged
    ]
    return {
        "category": lead["category"],
        "subcategory": lead["subcategory"],
        "source": "maskrcnn",
        "confidence": lead["confidence"],
        "displayName": lead["subcategory"],
        "usedFallback": False,
        "color": lead.get("color"),
        "secondaryColor": lead.get("secondaryColor"),
        "primaryColor": lead.get("primaryColor") or lead.get("color"),
        "secondaryColors": lead.get("secondaryColors") or (
            [lead["secondaryColor"]] if lead.get("secondaryColor") else []
        ),
        "accentColors": lead.get("accentColors") or [],
        "colorDistribution": lead.get("colorDistribution") or {},
        "pattern": lead.get("pattern") or "solid",
        "patternType": lead.get("patternType") or "solid",
        "isMulticolor": bool(lead.get("isMulticolor")),
        "colorClusters": lead.get("colorClusters") or [],
        "message": message,
        "items": others,
        "detected": merged,
        "detections": detections,
        "isolatedProduct": False,
        "detectionStrategy": "maskrcnn",
        "personBox": None,
        "maskrcnn": maskrcnn_detector.status(),
    }


def _classify_crop(
    crop: Image.Image,
    allowed: frozenset[str],
    classify_clothing,
) -> dict[str, Any]:
    """Accessory-role crops use the bag gate first so a tote is not a skirt."""
    accessory_allowed = allowed & accessory_classifier.TRUE_ACCESSORIES
    if accessory_allowed:
        if crop_foreground_occupancy(crop) < 0.08:
            return {"subcategory": "unknown", "usedFallback": True, "confidence": 0.0}
        pants_hit = None
        if "trousers" in allowed or "jeans" in allowed:
            pants_hit = trousers_gate.lock_or_prefer_trousers(crop)
        skirt_hit = None
        if "skirt" in allowed or "miniskirt" in allowed:
            skirt_hit = skirt_gate.lock_or_prefer_skirt(crop)
        jacket_hit = None
        if "jacket" in allowed:
            jacket_hit = jacket_gate.lock_or_prefer_jacket(
                crop, hanging=is_hanging_body_garment(crop)
            )
        if jacket_hit is not None and pants_hit is None and skirt_hit is None:
            return jacket_hit
        tshirt_hit = None
        if "t-shirt" in allowed:
            tshirt_hit = tshirt_gate.lock_or_prefer_tshirt(
                crop, hanging=is_hanging_body_garment(crop)
            )
        if tshirt_hit is not None and pants_hit is None and skirt_hit is None:
            return tshirt_hit
        shoes_hit = None
        if "shoes" in allowed or "loafers" in allowed:
            shoes_hit = shoes_gate.lock_or_prefer_shoes(
                crop, hanging=is_hanging_body_garment(crop)
            )
        sneakers_hit = None
        if "sneakers" in allowed or "shoes" in allowed:
            sneakers_hit = sneakers_gate.lock_or_prefer_sneakers(
                crop, hanging=is_hanging_body_garment(crop)
            )
        heels_hit = None
        if "heels" in allowed or "shoes" in allowed:
            heels_hit = heels_gate.lock_or_prefer_heels(
                crop, hanging=is_hanging_body_garment(crop)
            )
        if shoes_hit is not None and pants_hit is None and skirt_hit is None:
            shoes_s = float(shoes_hit["confidence"])
            sneaker_s = float(sneakers_hit["confidence"]) if sneakers_hit is not None else 0.0
            heels_s = float(heels_hit["confidence"]) if heels_hit is not None else 0.0
            if not (
                (sneakers_hit is not None and sneaker_s >= shoes_s + 0.28)
                or (
                    heels_hit is not None
                    and heels_s >= 0.88
                    and heels_s >= shoes_s + 0.15
                )
            ):
                return shoes_hit
        if sneakers_hit is not None and pants_hit is None and skirt_hit is None:
            return sneakers_hit
        if heels_hit is not None and pants_hit is None and skirt_hit is None:
            return heels_hit
        flats_hit = None
        if "flats" in allowed or "shoes" in allowed or "loafers" in allowed:
            flats_hit = flats_gate.lock_or_prefer_flats(
                crop, hanging=is_hanging_body_garment(crop)
            )
        if flats_hit is not None and pants_hit is None and skirt_hit is None:
            return flats_hit
        shirt_hit = None
        if "shirt" in allowed or "t-shirt" in allowed:
            shirt_hit = shirt_gate.lock_or_prefer_shirt(crop)
        if shirt_hit is not None and pants_hit is None and skirt_hit is None:
            return shirt_hit
        locked_hat = hat_gate.prefer_hat_over_bag(crop)
        if locked_hat is not None:
            rival = watch_gate.prefer_watch_over_bag(
                crop
            ) or watch_belt_gate.prefer_belt_over_bag(crop)
            if rival is None:
                rival = skirt_hit or skirt_gate.lock_or_prefer_skirt(crop)
            if rival is None:
                rival = shirt_hit
            if rival is None:
                rival = flats_hit
            if rival is None:
                rival = heels_hit
            if rival is None:
                rival = sneakers_hit
            if rival is None:
                return locked_hat
        locked_watch = watch_gate.prefer_watch_over_bag(crop) or watch_gate.lock_watch(
            crop
        )
        if locked_watch is not None:
            if dupatta_gate.prefer_dupatta_over_bag(crop) is None:
                return locked_watch
        locked_dupatta = dupatta_gate.prefer_dupatta_over_bag(
            crop
        ) or dupatta_gate.lock_dupatta(crop)
        if locked_dupatta is not None and pants_hit is None and skirt_hit is None and shirt_hit is None:
            return locked_dupatta
        locked_belt = watch_belt_gate.prefer_belt_over_bag(crop)
        if locked_belt is not None and pants_hit is None and skirt_hit is None and shirt_hit is None:
            return locked_belt
        if "bag" in accessory_allowed:
            locked = bag_gate.lock_bag(crop)
            if locked is not None:
                return locked
        if (
            "hat" in accessory_allowed
            and not bag_gate.looks_like_bag(crop)
            and shirt_hit is None
        ):
            locked_hat = hat_gate.lock_hat(crop)
            if locked_hat is not None:
                return locked_hat
        if "watch" in accessory_allowed:
            locked_watch = watch_gate.lock_watch(crop)
            if locked_watch is not None:
                return locked_watch
        if (
            ("dupatta" in accessory_allowed or "scarf" in accessory_allowed)
            and shirt_hit is None
        ):
            locked_dupatta = dupatta_gate.lock_dupatta(crop)
            if locked_dupatta is not None:
                return locked_dupatta
        if "belt" in accessory_allowed and not bag_gate.looks_like_bag(crop):
            locked_belt = watch_belt_gate.lock_belt(crop)
            if locked_belt is not None:
                return locked_belt
        accessory = accessory_classifier.classify_accessory(crop)
        if (
            accessory is not None
            and not accessory.get("usedFallback")
            and accessory.get("subcategory") in accessory_allowed
        ):
            return accessory
        if allowed <= accessory_classifier.TRUE_ACCESSORIES:
            return accessory or {"subcategory": "unknown", "usedFallback": True}
    return classify_clothing(crop)


def _classify_proposal(
    image: Image.Image,
    proposal: Proposal,
    classify_clothing,
) -> dict[str, Any] | None:
    """Confirm a detector box with the existing classifiers.

    The detector only says "there is a bag-like object here". The wardrobe
    label still has to come from MobileNetV2, and an unconfirmed box is
    dropped rather than trusted on the detector's word.
    """
    settings = get_settings()
    box = normalize_bbox(proposal.bbox)
    if box is None:
        return None
    crop = _crop(image, (box[0], box[1], box[2], box[3]))
    if crop is None:
        return None
    allowed = proposal.allowed or frozenset()
    if accessory_allowed := (allowed & accessory_classifier.TRUE_ACCESSORIES):
        if crop_foreground_occupancy(crop) < 0.10:
            return None
        # Fashionpedia accessory boxes are trusted at a lower floor than COCO bags.
        min_det = 0.28 if proposal.source == "fashionpedia" else 0.55
        if float(proposal.confidence) < min_det:
            return None
    result = _classify_crop(crop, allowed, classify_clothing)
    label = result.get("subcategory") or "unknown"
    if result.get("usedFallback") or label == "unknown":
        return None
    if allowed and label not in allowed:
        return None
    if float(result.get("confidence") or 0) < settings.refine_min_confidence:
        return None
    crop_colors = analyze_garment_colors(crop).to_api()
    item = _as_item(
        result,
        color=crop_colors.get("color"),
        secondary=crop_colors.get("secondaryColor"),
        bbox=list(box),
        region=proposal.region or "detect",
        extra=crop_colors,
    )
    if item is not None and proposal.detector_label:
        item["detectorLabel"] = proposal.detector_label
        item["detectorConfidence"] = round(float(proposal.confidence), 4)
        item["refinedLabel"] = item["subcategory"]
        item["refinedConfidence"] = item["confidence"]
    return item


def _should_scan_regions(
    image: Image.Image,
    primary: dict[str, Any],
    *,
    person: list[float] | None = None,
) -> bool:
    if is_closeup_item_frame(image):
        return False
    # No person + hanging pants/shirt: whole-image classify only.
    if person is None and (
        is_hanging_body_garment(image)
        or (primary.get("subcategory") or "")
        in {"trousers", "jeans", "shorts", "skirt", "shirt", "t-shirt", "hat"}
    ):
        return False
    width, height = image.size
    tall = height >= int(width * 1.22)
    extras = primary.get("items") or []
    dress = (primary.get("subcategory") or "") in {"dress", "gown", "modest dress"}
    return tall or len(extras) >= 1 or dress


def _crop(image: Image.Image, box: tuple[float, float, float, float]) -> Image.Image | None:
    min_side = get_settings().min_crop_px
    width, height = image.size
    x1, y1, x2, y2 = box
    left, top = int(x1 * width), int(y1 * height)
    right, bottom = int(x2 * width), int(y2 * height)
    if right - left < min_side or bottom - top < min_side:
        return None
    return image.crop((left, top, right, bottom))


def _as_item(
    raw: dict[str, Any],
    *,
    color: str | None = None,
    secondary: str | None = None,
    bbox: list[float] | None,
    region: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    label = str(raw.get("subcategory") or "unknown")
    if label == "unknown":
        return None
    confidence = float(raw.get("confidence") or 0)
    if confidence < get_settings().item_min_confidence:
        return None
    category = str(raw.get("category") or family_of(label))
    item = {
        "category": category,
        "subcategory": label,
        "confidence": confidence,
        "color": color or raw.get("color"),
        "secondaryColor": secondary or raw.get("secondaryColor"),
        "bbox": bbox,
        "source": raw.get("source") or region,
        "region": region,
        "usedFallback": bool(raw.get("usedFallback")),
    }
    if extra:
        for key, value in extra.items():
            if key in {"category", "subcategory", "confidence", "bbox", "source", "region"}:
                continue
            item[key] = value
        if extra.get("color"):
            item["color"] = extra["color"]
        if extra.get("secondaryColor") is not None:
            item["secondaryColor"] = extra["secondaryColor"]
    return item


def _merge(items: list[dict[str, Any]], *, closeup: bool = False) -> list[dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for item in items:
        key = item["subcategory"]
        prev = best.get(key)
        if prev is None or float(item["confidence"]) > float(prev["confidence"]):
            best[key] = item
    merged = list(best.values())
    dress = next((row for row in merged if row["subcategory"] == "dress"), None)
    pants = [
        row
        for row in merged
        if row["subcategory"] in {"trousers", "jeans", "shorts"}
    ]
    best_pants = (
        max(pants, key=lambda row: float(row["confidence"])) if pants else None
    )
    # trousers_gate locked pants: do not let a dress/shirt leftover lead.
    if (
        best_pants is not None
        and best_pants.get("source") == "trousers_gate"
        and best_pants["subcategory"] in {"trousers", "jeans"}
        and float(best_pants["confidence"]) >= 0.38
    ):
        merged = [
            row
            for row in merged
            if row["subcategory"] not in {"dress", "shirt", "t-shirt"}
        ]
        merged.sort(
            key=lambda row: (
                0 if row["subcategory"] in {"trousers", "jeans"} else 1,
                -float(row["confidence"]),
            )
        )
        return merged
    # Laid-flat pants are often also labeled dress. A competitive pants
    # score is the garment; the dress leftover must not lead or strip it.
    if (
        dress is not None
        and best_pants is not None
        and float(best_pants["confidence"]) >= 0.50
        and float(best_pants["confidence"])
        >= float(dress["confidence"]) * 0.75
    ):
        merged = [row for row in merged if row["subcategory"] != "dress"]
        dress = None
    elif dress is not None:
        merged = [
            row
            for row in merged
            if row["subcategory"] == "dress"
            or family_of(row["subcategory"]) != "lowerwear"
        ]
    family_rank = {
        "dress": 0,
        "upperwear": 1,
        "lowerwear": 2,
        "footwear": 3,
        "accessories": 4,
    }
    # Isolated bag photos often also emit skirt (silhouette) or hat
    # (backpack top). Bag is the object; those leftovers must not lead.
    has_bag = any(row["subcategory"] == "bag" for row in merged)
    has_hat = any(row["subcategory"] == "hat" for row in merged)
    has_skirt = any(row["subcategory"] == "skirt" for row in merged)
    skirt_row = next((row for row in merged if row["subcategory"] == "skirt"), None)
    if (
        skirt_row is not None
        and skirt_row.get("source") == "skirt_gate"
        and float(skirt_row["confidence"]) >= 0.38
    ):
        merged = [
            row for row in merged if row["subcategory"] not in {"hat", "belt"}
        ]
        merged.sort(
            key=lambda row: (
                0 if row["subcategory"] == "skirt" else 1,
                -float(row["confidence"]),
            )
        )
        return merged
    jacket_row = next((row for row in merged if row["subcategory"] == "jacket"), None)
    if (
        jacket_row is not None
        and jacket_row.get("source") == "jacket_gate"
        and float(jacket_row["confidence"]) >= 0.40
    ):
        merged = [
            row
            for row in merged
            if row["subcategory"] not in {"hat", "shirt", "t-shirt"}
        ]
        merged.sort(
            key=lambda row: (
                0 if row["subcategory"] == "jacket" else 1,
                -float(row["confidence"]),
            )
        )
        return merged
    tshirt_row = next((row for row in merged if row["subcategory"] == "t-shirt"), None)
    if (
        tshirt_row is not None
        and tshirt_row.get("source") == "tshirt_gate"
        and float(tshirt_row["confidence"]) >= 0.50
    ):
        merged = [
            row
            for row in merged
            if row["subcategory"] not in {"hat", "shirt", "dupatta", "dress"}
        ]
        merged.sort(
            key=lambda row: (
                0 if row["subcategory"] == "t-shirt" else 1,
                -float(row["confidence"]),
            )
        )
        return merged
    shoes_row = next((row for row in merged if row["subcategory"] == "shoes"), None)
    sneakers_row = next((row for row in merged if row["subcategory"] == "sneakers"), None)
    if (
        shoes_row is not None
        and shoes_row.get("source") == "shoes_gate"
        and float(shoes_row["confidence"]) >= 0.40
        and not (
            sneakers_row is not None
            and sneakers_row.get("source") == "sneakers_gate"
            and float(sneakers_row["confidence"]) >= float(shoes_row["confidence"]) + 0.10
        )
    ):
        merged = [
            row
            for row in merged
            if row["subcategory"] not in {"hat", "dress"}
        ]
        merged.sort(
            key=lambda row: (
                0 if row["subcategory"] == "shoes" else 1,
                -float(row["confidence"]),
            )
        )
        return merged
    sneakers_row = next((row for row in merged if row["subcategory"] == "sneakers"), None)
    if (
        sneakers_row is not None
        and sneakers_row.get("source") == "sneakers_gate"
        and float(sneakers_row["confidence"]) >= 0.40
    ):
        merged = [
            row
            for row in merged
            if row["subcategory"] not in {"hat", "flats", "dress"}
        ]
        merged.sort(
            key=lambda row: (
                0 if row["subcategory"] == "sneakers" else 1,
                -float(row["confidence"]),
            )
        )
        return merged
    heels_row = next((row for row in merged if row["subcategory"] == "heels"), None)
    flats_row = next((row for row in merged if row["subcategory"] == "flats"), None)
    strong_flats = (
        flats_row is not None
        and flats_row.get("source") == "flats_gate"
        and float(flats_row["confidence"])
        > float((heels_row or {}).get("confidence") or 0) + 0.05
    )
    if (
        heels_row is not None
        and heels_row.get("source") == "heels_gate"
        and float(heels_row["confidence"]) >= 0.40
        and not strong_flats
    ):
        merged = [
            row
            for row in merged
            if row["subcategory"] not in {"hat", "shirt", "dress"}
        ]
        merged.sort(
            key=lambda row: (
                0 if row["subcategory"] == "heels" else 1,
                -float(row["confidence"]),
            )
        )
        return merged
    flats_row = next((row for row in merged if row["subcategory"] == "flats"), None)
    if (
        flats_row is not None
        and flats_row.get("source") == "flats_gate"
        and float(flats_row["confidence"]) >= 0.40
    ):
        merged = [
            row for row in merged if row["subcategory"] not in {"hat"}
        ]
        merged.sort(
            key=lambda row: (
                0 if row["subcategory"] == "flats" else 1,
                -float(row["confidence"]),
            )
        )
        return merged
    shirt_row = next((row for row in merged if row["subcategory"] == "shirt"), None)
    if (
        shirt_row is not None
        and shirt_row.get("source") == "shirt_gate"
        and float(shirt_row["confidence"]) >= 0.38
    ):
        merged = [
            row
            for row in merged
            if row["subcategory"] not in {"hat", "dupatta", "dress"}
        ]
        merged.sort(
            key=lambda row: (
                0 if row["subcategory"] == "shirt" else 1,
                -float(row["confidence"]),
            )
        )
        return merged
    footwear = {
        "heels",
        "shoes",
        "sneakers",
        "flats",
        "boots",
        "sandals",
        "loafers",
    }
    closeup_footwear = (
        closeup
        and not has_bag
        and not has_hat
        and any(
            row["subcategory"] in footwear
            and float(row["confidence"]) >= 0.30
            and row.get("source") in {"imagenet", "flats_gate", "heels_gate", "sneakers_gate", "shoes_gate", "footwear"}
            for row in merged
        )
    )
    # A shoe photographed alone can be mistaken for two trouser legs by a
    # lowerwear head. The footwear item is the actual close-up object.
    if closeup_footwear:
        merged = [
            row
            for row in merged
            if row["subcategory"] in footwear
            or family_of(row["subcategory"]) != "lowerwear"
        ]
        merged.sort(
            key=lambda row: (
                0 if row["subcategory"] in footwear else 1,
                -float(row["confidence"]),
            )
        )
        return merged
    # Isolated beanie / cap photos also emit skirt (letter band, hem-like
    # crop). That leftover must not lead over Hat.
    if closeup and has_hat and has_skirt and dress is None and not has_bag:
        merged = [row for row in merged if row["subcategory"] != "skirt"]
        merged.sort(
            key=lambda row: (
                0 if row["subcategory"] == "hat" else 1,
                -float(row["confidence"]),
            )
        )
        return merged
    # Caps misrouted through the shorts head: drop shorts/trousers leftovers.
    if closeup and has_hat and best_pants is not None and dress is None and not has_bag:
        merged = [
            row
            for row in merged
            if row["subcategory"] not in {"shorts", "trousers", "jeans", "skirt"}
        ]
        merged.sort(
            key=lambda row: (
                0 if row["subcategory"] == "hat" else 1,
                -float(row["confidence"]),
            )
        )
        return merged
    # Confident pants/jeans product: never let a side-band bag lead.
    if (
        best_pants is not None
        and float(best_pants["confidence"]) >= 0.50
        and has_bag
        and dress is None
    ):
        merged = [row for row in merged if row["subcategory"] != "bag"]
        has_bag = False
    # Strong trousers/shorts must lead over a weak ImageNet top (blazer/suit).
    if best_pants is not None and float(best_pants["confidence"]) >= 0.55:
        others = [
            row
            for row in merged
            if row["subcategory"] not in {"trousers", "jeans", "shorts"}
        ]
        top_other = (
            max(others, key=lambda row: float(row["confidence"])) if others else None
        )
        if top_other is None or float(best_pants["confidence"]) >= float(
            top_other["confidence"]
        ) + 0.20:
            merged.sort(
                key=lambda row: (
                    0
                    if row["subcategory"] in {"trousers", "jeans", "shorts"}
                    else 1,
                    -float(row["confidence"]),
                )
            )
            return merged
    if closeup and has_hat:
        hat_row = max(
            (row for row in merged if row["subcategory"] == "hat"),
            key=lambda row: float(row["confidence"]),
        )
        if (
            hat_row.get("source") == "hat_gate"
            and float(hat_row["confidence"]) >= 0.48
        ):
            merged.sort(
                key=lambda row: (
                    0 if row["subcategory"] == "hat" else 1,
                    -float(row["confidence"]),
                )
            )
            return merged
    has_watch = any(row["subcategory"] == "watch" for row in merged)
    has_belt = any(row["subcategory"] == "belt" for row in merged)
    if closeup and has_watch:
        watch_row = max(
            (row for row in merged if row["subcategory"] == "watch"),
            key=lambda row: float(row["confidence"]),
        )
        if (
            watch_row.get("source") in {"watch_gate", "watch_belt_gate"}
            and float(watch_row["confidence"]) >= 0.48
        ):
            merged.sort(
                key=lambda row: (
                    0 if row["subcategory"] == "watch" else 1,
                    -float(row["confidence"]),
                )
            )
            return merged
    has_dupatta = any(row["subcategory"] == "dupatta" for row in merged)
    if closeup and has_dupatta:
        dupatta_row = max(
            (row for row in merged if row["subcategory"] == "dupatta"),
            key=lambda row: float(row["confidence"]),
        )
        if (
            dupatta_row.get("source") == "dupatta_gate"
            and float(dupatta_row["confidence"]) >= 0.48
        ):
            merged.sort(
                key=lambda row: (
                    0 if row["subcategory"] == "dupatta" else 1,
                    -float(row["confidence"]),
                )
            )
            return merged
    if closeup and has_belt:
        belt_row = max(
            (row for row in merged if row["subcategory"] == "belt"),
            key=lambda row: float(row["confidence"]),
        )
        if (
            belt_row.get("source") == "watch_belt_gate"
            and float(belt_row["confidence"]) >= 0.48
        ):
            merged.sort(
                key=lambda row: (
                    0 if row["subcategory"] == "belt" else 1,
                    -float(row["confidence"]),
                )
            )
            return merged
    if has_bag and dress is None:
        # Real carried bags can still lead — only when no strong pants item.
        merged.sort(
            key=lambda row: (
                0 if row["subcategory"] == "bag" else 1,
                family_rank.get(family_of(row["subcategory"]), 9),
                -float(row["confidence"]),
            )
        )
        return merged
    leaf_rank = {"bag": 0, "hat": 1}
    merged.sort(
        key=lambda row: (
            family_rank.get(family_of(row["subcategory"]), 9),
            leaf_rank.get(row["subcategory"], 2),
            -float(row["confidence"]),
        )
    )
    return merged
