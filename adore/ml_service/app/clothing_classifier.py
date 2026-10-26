"""Clothing classifier used by POST /analyze-clothing.

Preference order:
1. ImageNet for hats / sunglasses / watch / belt / scarf
2. Bag-vs-shoes MobileNetV2 specialist (stops handbags becoming jewellery or shoes)
3. ImageNet jewellery only when the bag/shoes specialist is unsure
4. 3-class lowerwear MobileNetV2 (trousers vs shorts vs skirt)
5. 3-class silhouette MobileNetV2 (long dress vs pants vs long skirt)
6. Fine-tuned wardrobe MobileNetV2, then ImageNet
7. Unknown/Uncertain if confidence is too low
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .clothing_taxonomy import (
    ACCESSORY_CLASSES,
    CLASS_TO_CATEGORY,
    FOOTWEAR,
    PANTS_LABELS,
    UPPERWEAR_KEEP,
    apply_family_constraints,
    extra_items,
    family_of,
    is_closeup_item_frame,
    is_full_length_frame,
    is_hanging_body_garment,
    preprocess_mobilenet_v2,
)
from . import accessory_classifier
from . import bag_gate
from . import dress_upperwear_gate
from . import hat_gate
from . import object_detector
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
from . import footwear_classifier
from . import garment_classifier
from . import lowerwear5
from . import lowerwear_classifier
from . import silhouette_classifier

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
FINETUNED_CANDIDATES = (
    MODELS_DIR / "clothing_mobilenetv2.keras",
    MODELS_DIR / "clothing_mobilenetv2.h5",
)
IMAGENET_WEIGHT_CANDIDATES = (
    MODELS_DIR / "mobilenet_v2_imagenet_1.0_224.h5",
    MODELS_DIR / "mobilenet_v2_weights_tf_dim_ordering_tf_kernels_1.0_224.h5",
    Path(
        r"D:\fyp project\outfit"
        r"\mobilenet_v2_weights_tf_dim_ordering_tf_kernels_1.0_224 (1).h5"
    ),
)

IMAGENET_TO_CLOTHING: dict[str, tuple[str, str]] = {
    "jersey": ("upperwear", "t-shirt"),
    "sweatshirt": ("upperwear", "hoodie"),
    "cardigan": ("upperwear", "cardigan"),
    "suit": ("upperwear", "blazer"),
    "bow_tie": ("accessories", "jewelry"),
    "bow tie": ("accessories", "jewelry"),
    "windsor_tie": ("accessories", "jewelry"),
    "windsor tie": ("accessories", "jewelry"),
    "lab_coat": ("upperwear", "coat"),
    "lab coat": ("upperwear", "coat"),
    "fur_coat": ("upperwear", "coat"),
    "fur coat": ("upperwear", "coat"),
    "cloak": ("upperwear", "coat"),
    "kimono": ("upperwear", "kurta"),
    "abaya": ("upperwear", "abaya"),
    "jean": ("lowerwear", "jeans"),
    "miniskirt": ("lowerwear", "skirt"),
    "mini skirt": ("lowerwear", "skirt"),
    "overskirt": ("lowerwear", "skirt"),
    "over skirt": ("lowerwear", "skirt"),
    "hoopskirt": ("lowerwear", "skirt"),
    "hoop skirt": ("lowerwear", "skirt"),
    "sarong": ("lowerwear", "skirt"),
    "pajama": ("upperwear", "shirt"),
    "gown": ("dress", "gown"),
    "academic_gown": ("dress", "gown"),
    "academic gown": ("dress", "gown"),
    "bikini": ("upperwear", "t-shirt"),
    "swimming_trunks": ("lowerwear", "shorts"),
    "swimming trunks": ("lowerwear", "shorts"),
    "running_shoe": ("footwear", "sneakers"),
    "running shoe": ("footwear", "sneakers"),
    "Loafer": ("footwear", "loafers"),
    "loafer": ("footwear", "loafers"),
    "cowboy_boot": ("footwear", "boots"),
    "cowboy boot": ("footwear", "boots"),
    "sandal": ("footwear", "sandals"),
    "clog": ("footwear", "shoes"),
    "cowboy_hat": ("accessories", "hat"),
    "cowboy hat": ("accessories", "hat"),
    "sombrero": ("accessories", "hat"),
    "bonnet": ("accessories", "hat"),
    "bathing cap": ("accessories", "hat"),
    "shower cap": ("accessories", "hat"),
    "mortarboard": ("accessories", "hat"),
    "pickelhaube": ("accessories", "hat"),
    "bearskin": ("accessories", "hat"),
    "crash helmet": ("accessories", "hat"),
    "football helmet": ("accessories", "hat"),
    "backpack": ("accessories", "bag"),
    "purse": ("accessories", "bag"),
    "mailbag": ("accessories", "bag"),
    "plastic bag": ("accessories", "bag"),
    "shopping basket": ("accessories", "bag"),
    "suitcase": ("accessories", "bag"),
    "wallet": ("accessories", "bag"),
    "pencil_box": ("accessories", "bag"),
    "pencil box": ("accessories", "bag"),
    "hamper": ("accessories", "bag"),
    "handkerchief": ("accessories", "scarf"),
    "stole": ("accessories", "scarf"),
    "feather boa": ("accessories", "scarf"),
    "necklace": ("accessories", "jewelry"),
    "hair slide": ("accessories", "jewelry"),
    "sunglasses": ("accessories", "sunglasses"),
    "sunglass": ("accessories", "sunglasses"),
    "buckle": ("accessories", "belt"),
    "seat belt": ("accessories", "belt"),
    "digital watch": ("accessories", "watch"),
    "analog clock": ("accessories", "watch"),
    "stopwatch": ("accessories", "watch"),
    "trench coat": ("upperwear", "coat"),
    "military uniform": ("upperwear", "jacket"),
    "chain": ("accessories", "jewelry"),
    "bolo tie": ("accessories", "jewelry"),
    "ski_mask": ("accessories", "hat"),
    "ski mask": ("accessories", "hat"),
    "packet": ("accessories", "bag"),
}

_loaded = False
_finetuned: Any = None
_finetuned_labels: list[str] = []
_imagenet: Any = None
_imagenet_decode: Any = None
_imagenet_backend = "none"
_imagenet_weights = ""
_load_error = ""


def model_status() -> dict[str, Any]:
    _ensure_loaded()
    return {
        "finetuned": _finetuned is not None,
        "silhouette": silhouette_classifier.status(),
        "lowerwear": lowerwear_classifier.status(),
        "accessory": accessory_classifier.status(),
        "bagGate": bag_gate.status(),
        "hatGate": hat_gate.status(),
        "watchGate": watch_gate.status(),
        "dupattaGate": dupatta_gate.status(),
        "trousersGate": trousers_gate.status(),
        "skirtGate": skirt_gate.status(),
        "shirtGate": shirt_gate.status(),
        "tshirtGate": tshirt_gate.status(),
        "jacketGate": jacket_gate.status(),
        "flatsGate": flats_gate.status(),
        "heelsGate": heels_gate.status(),
        "sneakersGate": sneakers_gate.status(),
        "shoesGate": shoes_gate.status(),
        "watchBeltGate": watch_belt_gate.status(),
        "footwear": footwear_classifier.status(),
        "garment4": garment_classifier.status(),
        "lowerwear5": lowerwear5.status(),
        "imagenet": _imagenet_backend,
        "imagenetWeights": _imagenet_weights,
        "classes": list(_finetuned_labels),
        "error": _load_error,
    }


def _local_imagenet_weights() -> Path | None:
    for path in IMAGENET_WEIGHT_CANDIDATES:
        if path.is_file():
            return path
    return None


def _ensure_loaded() -> None:
    global _loaded
    if _loaded:
        return
    _load_finetuned()
    _load_imagenet()
    _loaded = True


def _load_finetuned() -> None:
    global _finetuned, _finetuned_labels, _load_error
    labels_path = MODELS_DIR / "labels.json"
    if labels_path.is_file():
        try:
            payload = json.loads(labels_path.read_text(encoding="utf-8"))
            _finetuned_labels = list(payload.get("classes") or [])
        except json.JSONDecodeError as exc:
            _load_error = f"labels.json is invalid: {exc}"
    for path in FINETUNED_CANDIDATES:
        if not path.is_file():
            continue
        try:
            from tensorflow.keras.models import load_model

            _finetuned = load_model(path)
            if not _finetuned_labels:
                units = int(_finetuned.output_shape[-1])
                _finetuned_labels = [f"class_{i}" for i in range(units)]
            return
        except Exception as exc:  # noqa: BLE001
            _load_error = f"{path.name}: {exc}"
            _finetuned = None


def _build_mobilenet_v2(weights_arg: str | None):
    """Build 224×224, alpha=1.0, ImageNet-head MobileNetV2."""
    try:
        from tensorflow.keras.applications.mobilenet_v2 import (
            MobileNetV2,
            decode_predictions,
        )

        model = MobileNetV2(
            input_shape=(224, 224, 3),
            alpha=1.0,
            include_top=True,
            weights=weights_arg,
            classes=1000,
        )
        return model, decode_predictions, "tensorflow"
    except Exception:
        pass
    try:
        from keras.applications.mobilenet_v2 import MobileNetV2, decode_predictions

        model = MobileNetV2(
            input_shape=(224, 224, 3),
            alpha=1.0,
            include_top=True,
            weights=weights_arg,
            classes=1000,
        )
        return model, decode_predictions, "keras"
    except Exception:
        return None, None, "none"


def _load_imagenet() -> None:
    global _imagenet, _imagenet_decode, _imagenet_backend
    global _imagenet_weights, _load_error
    local = _local_imagenet_weights()
    if local is not None:
        try:
            model, decode, backend = _build_mobilenet_v2(None)
            if model is None:
                raise RuntimeError("TensorFlow/Keras MobileNetV2 is not installed")
            try:
                model.load_weights(str(local))
            except ValueError:
                model.load_weights(str(local), by_name=True)
            _imagenet = model
            _imagenet_decode = decode
            _imagenet_backend = f"{backend}-local"
            _imagenet_weights = str(local)
            return
        except Exception as exc:  # noqa: BLE001
            _load_error = f"{local.name}: {exc}"
            try:
                model, decode, backend = _build_mobilenet_v2(str(local))
                if model is not None:
                    _imagenet = model
                    _imagenet_decode = decode
                    _imagenet_backend = f"{backend}-local"
                    _imagenet_weights = str(local)
                    return
            except Exception as inner:  # noqa: BLE001
                _load_error = f"{local.name}: {inner}"

    try:
        from tensorflow.keras.applications.mobilenet_v2 import (
            MobileNetV2,
            decode_predictions,
        )

        _imagenet = MobileNetV2(weights="imagenet")
        _imagenet_decode = decode_predictions
        _imagenet_backend = "tensorflow"
        _imagenet_weights = "imagenet"
        return
    except Exception:
        _imagenet = None
    try:
        from torchvision.models import MobileNet_V2_Weights, mobilenet_v2

        weights = MobileNet_V2_Weights.IMAGENET1K_V1
        model = mobilenet_v2(weights=weights)
        model.eval()
        _imagenet = (model, weights)
        _imagenet_backend = "torch"
        _imagenet_weights = "torchvision-imagenet1k"
    except Exception:
        _imagenet_backend = "unavailable"


def _has_bag_hint(result: dict[str, Any] | None, *, min_score: float = 0.12) -> bool:
    if result is None:
        return False
    if result.get("subcategory") == "bag" and float(result.get("confidence") or 0) >= 0.16:
        return True
    for row in result.get("ranked") or []:
        name = row.get("subcategory") if isinstance(row, dict) else None
        score = float(row.get("confidence") or 0) if isinstance(row, dict) else 0.0
        if name == "bag" and score >= min_score:
            return True
    for row in result.get("items") or []:
        if isinstance(row, dict) and row.get("subcategory") == "bag":
            return True
    return False


def _has_strong_bag_hint(result: dict[str, Any] | None) -> bool:
    return _has_bag_hint(result, min_score=0.20)


_PANTS_LABELS = PANTS_LABELS | {"shorts"}
_SHIRT_LIKE = frozenset(UPPERWEAR_KEEP)


def _pants_from_lowerwear(lowerwear: dict[str, Any] | None) -> dict[str, Any] | None:
    """Use the trousers/shorts/skirt head when it saw two-leg pants."""
    if lowerwear is None:
        return None
    label = lowerwear.get("subcategory")
    if (
        label in _PANTS_LABELS
        and not lowerwear.get("usedFallback")
        and float(lowerwear.get("confidence") or 0) >= 0.42
    ):
        return lowerwear
    trousers = max(
        _ranked_score(lowerwear, "trousers"),
        _ranked_score(lowerwear, "jeans"),
    )
    shorts = _ranked_score(lowerwear, "shorts")
    skirt = _ranked_score(lowerwear, "skirt")
    if trousers >= shorts and trousers >= 0.45 and trousers >= skirt:
        out = dict(lowerwear)
        out["subcategory"] = "trousers"
        out["category"] = "lowerwear"
        out["usedFallback"] = False
        out["source"] = "lowerwear"
        out["displayName"] = "Trousers/Pants"
        out["confidence"] = trousers
        out["message"] = f"Detected Trousers/Pants ({trousers * 100:.0f}%)."
        return out
    if shorts > trousers and shorts >= 0.45 and shorts >= skirt:
        out = dict(lowerwear)
        out["subcategory"] = "shorts"
        out["category"] = "lowerwear"
        out["usedFallback"] = False
        out["source"] = "lowerwear"
        out["displayName"] = "Shorts"
        out["confidence"] = shorts
        out["message"] = f"Detected Shorts ({shorts * 100:.0f}%)."
        return out
    return None


def _ranked_score(result: dict[str, Any] | None, name: str) -> float:
    if result is None:
        return 0.0
    for row in result.get("ranked") or []:
        if isinstance(row, dict) and row.get("subcategory") == name:
            return float(row.get("confidence") or 0)
    return 0.0


def _as_hat(accessory: dict[str, Any], extras: list[Any], hat_score: float) -> dict[str, Any]:
    hat = dict(accessory)
    hat["subcategory"] = "hat"
    hat["category"] = "accessories"
    hat["usedFallback"] = False
    hat["displayName"] = "Hat"
    hat["message"] = f"Detected Hat ({hat_score * 100:.0f}%)."
    if extras:
        hat["items"] = extras
    return hat


def _as_skirt(accessory: dict[str, Any], extras: list[Any], skirt_score: float) -> dict[str, Any]:
    skirt = dict(accessory)
    skirt["subcategory"] = "skirt"
    skirt["category"] = "lowerwear"
    skirt["usedFallback"] = False
    skirt["displayName"] = "Skirt"
    skirt["message"] = f"Detected Skirt ({skirt_score * 100:.0f}%)."
    if extras:
        skirt["items"] = extras
    return skirt


_ISOLATED_LOWERWEAR = {"shorts", "trousers", "jeans", "skirt", "miniskirt"}

# ImageNet / ranked names that count as topwear evidence (not hat/bag).
_TOPWEAR_HINTS = frozenset(
    {
        "shirt",
        "t-shirt",
        "jacket",
        "coat",
        "hoodie",
        "blazer",
        "sweater",
        "cardigan",
    }
)
_JACKET_HINTS = frozenset({"jacket", "coat", "blazer", "hoodie"})


def _attach_human_review(result: dict[str, Any]) -> dict[str, Any]:
    """Flag low-confidence / uncertain predictions for human review."""
    from .config import get_settings

    out = dict(result)
    threshold = float(get_settings().human_review_min_confidence)
    conf = float(out.get("confidence") or 0)
    sub = out.get("subcategory") or "unknown"
    needs = (
        conf < threshold
        or bool(out.get("usedFallback"))
        or sub == "unknown"
    )
    out["needsHumanReview"] = needs
    out["humanReviewThreshold"] = threshold
    if needs and not out.get("message"):
        out["message"] = (
            f"Low confidence ({conf * 100:.0f}% < {threshold * 100:.0f}%). "
            "Please confirm the garment type."
        )
    return out


def classify_clothing(image: Image.Image) -> dict[str, Any]:
    return _attach_human_review(_classify_clothing_core(image))


def _as_dress(confidence: float, extras: list[Any], source: str = "fashionpedia") -> dict[str, Any]:
    return {
        "category": "dress",
        "subcategory": "dress",
        "confidence": float(confidence),
        "usedFallback": False,
        "source": source,
        "message": f"Detected Dress ({float(confidence) * 100:.0f}%).",
        "displayName": "Dress",
        "items": extras or [],
    }


def _classify_clothing_core(image: Image.Image) -> dict[str, Any]:
    _ensure_loaded()
    imagenet = _classify_imagenet(image)
    finetuned = _classify_finetuned(image) if _finetuned is not None else None
    chosen = _prefer_accessory(imagenet, finetuned)
    label = (chosen or {}).get("subcategory") if chosen else "unknown"
    inet_sub = (imagenet or {}).get("subcategory") if imagenet else "unknown"
    extras = (chosen or {}).get("items") or []
    isolated = is_closeup_item_frame(image)
    hanging_body = is_hanging_body_garment(image)
    fp_hint = object_detector.fashionpedia_item_hint(image)
    fp_dress = float(fp_hint.get("dress") or 0.0)
    fp_shorts = float(fp_hint.get("shorts") or 0.0)
    fp_skirt = float(fp_hint.get("skirt") or 0.0)
    fp_hat = float(fp_hint.get("hat") or 0.0)
    fp_belt = float(fp_hint.get("belt") or 0.0)
    fp_watch = float(fp_hint.get("watch") or 0.0)
    fp_shoe = float(fp_hint.get("shoes") or 0.0)
    accessory = None
    pants_hit = None
    skirt_hit = None
    shirt_hit = None
    tshirt_hit = None
    jacket_hit = None
    flats_hit = None
    heels_hit = None
    sneakers_hit = None
    shoes_hit = None
    if label not in FOOTWEAR:
        pants_hit = trousers_gate.lock_or_prefer_trousers(image)
        skirt_hit = skirt_gate.lock_or_prefer_skirt(image)
        shirt_hit = shirt_gate.lock_or_prefer_shirt(image)
        tshirt_hit = tshirt_gate.lock_or_prefer_tshirt(image, hanging=hanging_body)
        jacket_hit = jacket_gate.lock_or_prefer_jacket(image, hanging=hanging_body)
    # Isolated flats are often ImageNet "flats"/"loafers" (FOOTWEAR) and
    # skip the upperwear gates, then hat_gate returns hat. Always ask the
    # flats specialist; hat/shirt/jacket modules are unchanged.
    flats_hit = flats_gate.lock_or_prefer_flats(image, hanging=hanging_body)
    # Tall ballet flats look like hanging garments, so the specialist
    # returns None. Isolated table-top flats still need a flats lock.
    if flats_hit is None and isolated:
        flats_hit = flats_gate.lock_or_prefer_flats(image, hanging=False)
    # Compact heels are stolen as shirt or flats. Always ask the heels
    # specialist; shirt/flats modules are unchanged.
    heels_hit = heels_gate.lock_or_prefer_heels(image, hanging=hanging_body)
    # Compact sneakers are stolen as hat or flats. Always ask the sneakers
    # specialist; hat/flats/heels modules are unchanged.
    sneakers_hit = sneakers_gate.lock_or_prefer_sneakers(image, hanging=hanging_body)
    # Compact oxfords are stolen as heels or sneakers. Always ask the
    # shoes specialist; heels/sneakers modules are unchanged.
    shoes_hit = shoes_gate.lock_or_prefer_shoes(image, hanging=hanging_body)

    # 6-class upperwear/dress head (shirt, t-shirt, hoodie, jacket, top, dress).
    # Consulted before binary jacket/shirt/t-shirt locks so a gown is not
    # returned as shirt and a hoodie is not collapsed to jacket.
    uw6 = None
    if label not in FOOTWEAR:
        uw6 = garment_classifier.classify_garment(image)
    uw6_sub = (uw6 or {}).get("subcategory")
    uw6_conf = float((uw6 or {}).get("confidence") or 0)
    pants_conf = float((pants_hit or {}).get("confidence") or 0)
    dress_beats_pants = (
        uw6_sub in {"dress", "gown"}
        and uw6_conf >= 0.50
        and (pants_hit is None or uw6_conf + 0.02 >= pants_conf)
    )
    uw6_is_upper = uw6_sub in {
        "shirt",
        "t-shirt",
        "hoodie",
        "jacket",
        "top",
        "dress",
        "gown",
        "coat",
        "blouse",
    }
    # The 6-class head must beat binary shirt/jacket/t-shirt locks. Those
    # gates have no hoodie/top/dress class, so they turn gowns into shirts.
    if (
        uw6 is not None
        and not uw6.get("usedFallback")
        and uw6_is_upper
        and uw6_conf >= 0.38
        and heels_hit is None
        and sneakers_hit is None
        and shoes_hit is None
        and flats_hit is None
        and (
            pants_hit is None
            or dress_beats_pants
            or (
                uw6_sub in {"shirt", "t-shirt", "hoodie", "jacket", "top", "coat"}
                and uw6_conf >= pants_conf + 0.06
            )
        )
        and (
            label not in _PANTS_LABELS | {"skirt", "miniskirt"}
            or dress_beats_pants
            or uw6_sub in {"shirt", "t-shirt", "hoodie", "jacket", "top"}
        )
    ):
        if extras:
            uw6["items"] = extras
        if uw6_sub in {"dress", "gown"}:
            uw6["category"] = "dress"
            if uw6_sub == "gown":
                uw6["subcategory"] = "dress"
        return uw6

    # 5-class lowerwear head (trousers, shorts, skirt, shalwar, leggings).
    # Consulted before binary trousers/skirt/shirt locks so shorts stay shorts
    # and shalwar/leggings are not collapsed to trousers.
    lw5 = None
    if label not in FOOTWEAR:
        lw5 = lowerwear5.classify_lowerwear5(image)
    lw5_sub = (lw5 or {}).get("subcategory")
    lw5_conf = float((lw5 or {}).get("confidence") or 0)
    dress_owns_lower = uw6_sub in {"dress", "gown"} and uw6_conf >= 0.45
    uw6_owns_upper = (
        uw6_sub in {"shirt", "t-shirt", "hoodie", "jacket", "top", "coat", "blouse"}
        and uw6_conf >= 0.32
    )
    if (
        lw5 is not None
        and not lw5.get("usedFallback")
        and heels_hit is None
        and sneakers_hit is None
        and shoes_hit is None
        and flats_hit is None
        and label not in {"hat", "watch", "belt", "dupatta", "bag"}
        and fp_hat < 0.32
        and fp_belt < 0.32
        and fp_watch < 0.32
        and not dress_owns_lower
        and not uw6_owns_upper
        and (
            (lw5_sub in {"shorts", "skirt", "shalwar", "leggings"} and lw5_conf >= 0.40)
            or (lw5_sub in {"trousers", "jeans"} and lw5_conf >= 0.52)
        )
    ):
        if extras:
            lw5["items"] = extras
        lw5["category"] = "lowerwear"
        return lw5

    # Binary jacket head. Shirt/hat/bag/lowerwear modules are unchanged;
    # a locked jacket wins over a weak ImageNet "bag" on a hanging coat.
    if jacket_hit is not None and label not in {"watch", "belt", "dupatta"} and label not in _PANTS_LABELS | {"skirt", "miniskirt"} and heels_hit is None and sneakers_hit is None and shoes_hit is None and fp_hat < 0.35 and fp_shorts < 0.40:
        dupatta_lock = dupatta_gate.lock_dupatta(image) or dupatta_gate.prefer_dupatta_over_bag(
            image
        )
        dupatta_conf = float(dupatta_lock["confidence"]) if dupatta_lock else 0.0
        jacket_conf = float(jacket_hit["confidence"])
        dupatta_owns = dupatta_conf >= 0.95 and dupatta_conf >= jacket_conf + 0.08
        lowerwear_blocks = pants_hit is not None or skirt_hit is not None
        pants_owns = pants_hit is not None and float(pants_hit["confidence"]) >= max(
            jacket_conf, 0.55
        )
        beats_lowerwear = label not in {
            "trousers",
            "jeans",
            "shorts",
            "skirt",
            "miniskirt",
        } and (hanging_body or jacket_conf >= 0.68)
        if pants_owns or label in _PANTS_LABELS | {"skirt", "miniskirt"}:
            beats_lowerwear = False
        if skirt_hit is not None and (
            not hanging_body
            or float(skirt_hit["confidence"]) >= jacket_conf + 0.06
        ):
            beats_lowerwear = False
        if not dupatta_owns and (not lowerwear_blocks or beats_lowerwear):
            if extras:
                jacket_hit["items"] = extras
            return jacket_hit

    # T-shirt vs collared shirt. Shirt/jacket modules are unchanged;
    # this only returns when the t-shirt specialist is sure.
    if (
        tshirt_hit is not None
        and heels_hit is None
        and sneakers_hit is None
        and shoes_hit is None
        and label not in {"bag", "watch", "belt", "dupatta", "jacket"}
        and label not in _PANTS_LABELS
        and label not in {"skirt", "miniskirt"}
        and not (
            not hanging_body
            and (
                hat_gate.lock_hat(image) is not None
                or hat_gate.prefer_hat_over_bag(image) is not None
            )
        )
    ):
        tee_conf = float(tshirt_hit["confidence"])
        lowerwear_blocks = pants_hit is not None or skirt_hit is not None
        pants_owns = pants_hit is not None and float(pants_hit["confidence"]) >= max(
            tee_conf, 0.55
        )
        beats_lowerwear = hanging_body or tee_conf >= 0.70
        if pants_owns or label in _PANTS_LABELS | {"skirt", "miniskirt"}:
            beats_lowerwear = False
        if lowerwear_blocks:
            beats_lowerwear = False
        if not lowerwear_blocks or beats_lowerwear:
            if extras:
                tshirt_hit["items"] = extras
            return tshirt_hit

    # Binary shoes head. Heels_gate and sneakers_gate have no oxford class,
    # so compact dress shoes become heels or sneakers. Return footwear/shoes
    # before those heads unless a more specific specialist is at least as
    # sure. Heels/sneakers modules are unchanged.
    if (
        shoes_hit is not None
        and label not in {"watch", "belt", "dupatta"}
        and not (
            bag_gate.looks_like_bag(image)
            and float(shoes_hit["confidence"]) < 0.72
        )
    ):
        shoes_s = float(shoes_hit["confidence"])
        sneaker_s = float(sneakers_hit["confidence"]) if sneakers_hit is not None else 0.0
        heels_s = float(heels_hit["confidence"]) if heels_hit is not None else 0.0
        # Tall product oxfords look like hanging shirts. Do not give those
        # to shirt_gate. Only a clearly stronger sneaker/heel specialist
        # may take the label. Shirt/heels modules are unchanged.
        prefer_sneakers = sneakers_hit is not None and sneaker_s >= shoes_s + 0.28
        prefer_heels = (
            heels_hit is not None
            and heels_s >= 0.88
            and heels_s >= shoes_s + 0.15
        )
        lowerwear_owns = hanging_body and (
            pants_hit is not None
            or skirt_hit is not None
            or label in _PANTS_LABELS
            or label in {"skirt", "miniskirt"}
        )
        # Compact oxfords stay shoes. Hanging pants/shorts/skirts must not
        # return here or lowerwear never runs. Shoes_gate is unchanged.
        if not prefer_sneakers and not prefer_heels and not lowerwear_owns:
            if extras:
                shoes_hit["items"] = extras
            return shoes_hit

    # Binary sneakers head. Hat_gate and flats_gate have no trainer class,
    # so compact sneakers become hat or flats. Return footwear/sneakers
    # before those heads. Hat/flats/heels modules are unchanged.
    if (
        sneakers_hit is not None
        and label not in _PANTS_LABELS
        and label not in {"skirt", "miniskirt", "watch", "belt", "dupatta"}
        and not (
            hanging_body
            and pants_hit is not None
            and float(pants_hit["confidence"])
            >= float(sneakers_hit["confidence"]) + 0.08
        )
        and not (
            hanging_body
            and skirt_hit is not None
            and label not in FOOTWEAR
        )
        and not (
            bag_gate.looks_like_bag(image)
            and float(sneakers_hit["confidence"]) < 0.72
        )
    ):
        if extras:
            sneakers_hit["items"] = extras
        return sneakers_hit

    # Binary flats head before heels. Tall flats used to skip this lock
    # (hanging=True) and then heels_gate stole them.
    if (
        flats_hit is not None
        and not (hanging_body and pants_hit is not None)
        and skirt_hit is None
        and label not in {"watch", "belt", "dupatta", "jacket", "t-shirt"}
        and not bag_gate.looks_like_bag(image)
        and not (
            heels_hit is not None
            and float(heels_hit["confidence"]) >= float(flats_hit["confidence"]) + 0.18
            and float(heels_hit["confidence"]) >= 0.78
        )
    ):
        if extras:
            flats_hit["items"] = extras
        return flats_hit

    # Binary heels head. Shirt_gate and flats_gate have no stiletto class,
    # so compact heels become shirt or flats. Return footwear/heels before
    # those heads on table-top shots. Flats_gate itself is unchanged.
    if (
        heels_hit is not None
        and flats_hit is None
        and label not in _PANTS_LABELS
        and label not in {"skirt", "miniskirt", "watch", "belt", "dupatta"}
        and not (
            hanging_body
            and pants_hit is not None
            and float(pants_hit["confidence"])
            >= float(heels_hit["confidence"]) + 0.08
        )
        and not (
            hanging_body
            and skirt_hit is not None
            and label not in FOOTWEAR
        )
        and not (
            bag_gate.looks_like_bag(image)
            and float(heels_hit["confidence"]) < 0.72
        )
    ):
        if extras:
            heels_hit["items"] = extras
        return heels_hit

    # New binary shirt head. Return shirt before hat/dupatta/dress.
    # Compact hats, watches, bags, and belts stay on those unchanged gates.
    compact_accessory = (
        isolated
        and not hanging_body
        and (
            label in {"hat", "watch", "bag", "belt", "dupatta", "jewelry"}
            or fp_hat >= 0.28
            or fp_belt >= 0.28
            or fp_watch >= 0.28
        )
    )
    if shirt_hit is not None and isolated:
        if hat_gate.lock_hat(image) or hat_gate.prefer_hat_over_bag(image):
            compact_accessory = True
        if watch_gate.lock_watch(image):
            compact_accessory = True
        if watch_belt_gate.lock_belt(image) or watch_belt_gate.prefer_belt_over_bag(image):
            compact_accessory = True
        if dupatta_gate.lock_dupatta(image) or dupatta_gate.prefer_dupatta_over_bag(image):
            compact_accessory = True
    keep_dupatta = label == "dupatta" and float(shirt_hit["confidence"] if shirt_hit else 0) < 0.62
    dress_owns = hanging_body and fp_dress >= 0.35 and fp_dress >= fp_hat and label not in {
        "hat",
        "watch",
        "belt",
        "bag",
    }
    if (
        shirt_hit is not None
        and not compact_accessory
        and not keep_dupatta
        and not dress_owns
        and not (pants_hit is not None and hanging_body)
        and not (
            skirt_hit is not None
            and (hanging_body or float(skirt_hit["confidence"]) >= 0.70)
        )
        and label not in {"bag", "watch", "belt", "hat", "dupatta"}
        and label not in _PANTS_LABELS
        and label not in {"skirt", "miniskirt"}
        and inet_sub not in _PANTS_LABELS
        and inet_sub not in {"skirt", "miniskirt", "hat"}
        and fp_hat < 0.32
        and fp_belt < 0.32
        and fp_watch < 0.32
        and fp_shorts < 0.32
        and fp_skirt < 0.32
    ):
        if extras:
            shirt_hit["items"] = extras
        return shirt_hit

    # Caps have no class in bag_gate, so run the hat specialist first.
    # Real bags stay bags: prefer_hat_over_bag requires a low bag score.
    if isolated or label in {
        "hat",
        "shirt",
        "t-shirt",
        "unknown",
        "cowboy_hat",
        "sombrero",
        "bonnet",
        "jewelry",
        "jacket",
        "hoodie",
        "bag",
        "skirt",
        "miniskirt",
        "dress",
        "flats",
        "shoes",
    }:
        locked_hat = hat_gate.prefer_hat_over_bag(image)
        if locked_hat is None and not bag_gate.looks_like_bag(image):
            locked_hat = hat_gate.lock_hat(image)
        if locked_hat is not None:
            rival = watch_gate.prefer_watch_over_bag(
                image
            ) or watch_belt_gate.prefer_belt_over_bag(image)
            if rival is None and not (isolated and not hanging_body):
                rival = skirt_hit
            if rival is None and not (isolated and not hanging_body):
                rival = shirt_hit
            if rival is None and not (isolated and not hanging_body):
                rival = jacket_hit
            if rival is None and not (isolated and not hanging_body):
                rival = tshirt_hit
            if rival is None:
                rival = flats_hit
            if rival is None:
                rival = heels_hit
            if rival is None:
                rival = sneakers_hit
            if rival is None:
                rival = shoes_hit
            if rival is None and hanging_body:
                rival = pants_hit
            if rival is not None:
                locked_hat = None
            else:
                if extras:
                    locked_hat["items"] = extras
                return locked_hat

    # Watch vs bag vs trousers. Do not skip when bag_gate thinks it is a
    # bag — that head has no watch class. Hat and bag modules are unchanged.
    if isolated or label in {
        "watch",
        "belt",
        "bag",
        "trousers",
        "jeans",
        "jewelry",
        "unknown",
        "skirt",
        "shirt",
        "t-shirt",
        "dress",
        "flats",
        "shoes",
        "sandals",
    }:
        locked_watch = watch_gate.prefer_watch_over_bag(image) or watch_gate.lock_watch(
            image
        )
        if locked_watch is not None:
            # Wrist close-ups stay watches. Hanging pants are not watches;
            # watch_gate still wins on compact isolated frames.
            skip_watch = (
                pants_hit is not None
                and (
                    hanging_body
                    or label in {"trousers", "jeans", "dress", "gown", "shirt", "t-shirt"}
                )
            ) or (
                skirt_hit is not None
                and (hanging_body or label in {"skirt", "miniskirt"})
            ) or (
                shirt_hit is not None
                and hanging_body
                and label in {"shirt", "t-shirt", "pajama"}
            ) or (
                jacket_hit is not None
                and hanging_body
                and label in {"jacket", "coat", "hoodie", "blazer"}
            ) or (
                tshirt_hit is not None
                and hanging_body
                and label in {"t-shirt", "jersey"}
            ) or (
                flats_hit is not None
                and label in FOOTWEAR
            ) or (
                heels_hit is not None
                and label in FOOTWEAR
            ) or (
                sneakers_hit is not None
                and label in FOOTWEAR
            ) or (
                shoes_hit is not None
                and label in FOOTWEAR
            )
            if dupatta_gate.prefer_dupatta_over_bag(image) is None and not skip_watch:
                if extras:
                    locked_watch["items"] = extras
                return locked_watch
        locked_dupatta = dupatta_gate.prefer_dupatta_over_bag(
            image
        ) or dupatta_gate.lock_dupatta(image)
        if locked_dupatta is not None and pants_hit is None:
            skip_dupatta = (
                isolated
                and not hanging_body
                and label not in {"dupatta", "scarf"}
                and (
                    fp_hat >= 0.22
                    or hat_gate.lock_hat(image) is not None
                    or hat_gate.prefer_hat_over_bag(image) is not None
                    or fp_watch >= 0.28
                    or fp_belt >= 0.28
                )
            ) or (
                skirt_hit is not None
                and (
                    label in {"skirt", "miniskirt"}
                    or hanging_body
                    or float(skirt_hit["confidence"])
                    >= float(locked_dupatta.get("confidence") or 0) + 0.06
                )
            ) or (
                shirt_hit is not None
                and label in {"shirt", "t-shirt", "pajama", "jersey"}
                and float(shirt_hit["confidence"])
                >= float(locked_dupatta.get("confidence") or 0) + 0.12
            ) or (
                tshirt_hit is not None
                and label in {"t-shirt", "jersey"}
            )
            if not skip_dupatta:
                if extras:
                    locked_dupatta["items"] = extras
                return locked_dupatta
        locked_belt = watch_belt_gate.prefer_belt_over_bag(image)
        if locked_belt is None and not bag_gate.looks_like_bag(image):
            locked_belt = watch_belt_gate.lock_belt(image)
        if (
            locked_belt is not None
            and pants_hit is None
            and skirt_hit is None
            and (
                shirt_hit is None
                or (
                    isolated
                    and not hanging_body
                    and float(locked_belt["confidence"]) >= 0.45
                )
            )
            and tshirt_hit is None
            and jacket_hit is None
            and label not in _PANTS_LABELS
            and label not in {"skirt", "miniskirt"}
        ):
            if extras:
                locked_belt["items"] = extras
            return locked_belt

    # Bag vs skirt vs flats is a dedicated gate. ImageNet miniskirt / loafer
    # on a tote must not win before this head runs.
    if isolated or label in {
        "bag",
        "skirt",
        "miniskirt",
        "flats",
        "shoes",
        "unknown",
        "dress",
        "jewelry",
        "sandals",
        "loafers",
        "heels",
    }:
        locked = bag_gate.lock_bag(image)
        if locked is not None:
            # bag_gate has no trousers class, so hanging pants score bag=1.0.
            # Compact product bags are not hanging_body — those stay bags.
            skip_bag = (
                pants_hit is not None
                and hanging_body
                and label not in {"bag"}
            ) or (
                skirt_hit is not None
                and label not in {"bag"}
                and (
                    hanging_body
                    or label
                    in {
                        "skirt",
                        "miniskirt",
                        "dress",
                        "unknown",
                        "shorts",
                    }
                )
            ) or (
                shirt_hit is not None
                and label not in {"bag"}
                and (
                    hanging_body
                    or label
                    in {
                        "shirt",
                        "t-shirt",
                        "pajama",
                        "unknown",
                        "hat",
                    }
                )
            ) or (
                jacket_hit is not None
                and hanging_body
            ) or (
                tshirt_hit is not None
                and hanging_body
                and label not in {"bag"}
            ) or (
                flats_hit is not None
                and label not in {"bag"}
            ) or (
                heels_hit is not None
                and label not in {"bag"}
            ) or (
                sneakers_hit is not None
                and label not in {"bag"}
            ) or (
                shoes_hit is not None
                and label not in {"bag"}
            ) or (
                fp_shoe >= 0.22
                and label not in {"bag"}
            )
            shirt_like_early = label in {
                "t-shirt",
                "shirt",
                "hoodie",
                "jacket",
                "coat",
                "sweater",
                "cardigan",
                "blazer",
            }
            if not skip_bag and not (
                hanging_body
                and shirt_like_early
                and float(locked.get("confidence") or 0) < 0.58
            ):
                if extras:
                    locked["items"] = extras
                return locked

    # Trousers vs dress vs shirt. Silhouette has no two-leg class and
    # garment4 has no trousers class, so hanging pants become dress/shirt.
    # Accessory gate modules above are unchanged.
    if pants_hit is not None and isolated and not hanging_body:
        if (
            fp_watch >= 0.28
            or fp_hat >= 0.28
            or fp_belt >= 0.28
            or watch_gate.lock_watch(image) is not None
            or hat_gate.lock_hat(image) is not None
        ):
            pants_hit = None
    if pants_hit is not None and shirt_hit is not None and not hanging_body and label in {
        "shirt",
        "t-shirt",
        "pajama",
        "jersey",
        "sweatshirt",
    }:
        pants_hit = None
    if (
        skirt_hit is not None
        and shirt_hit is not None
        and not hanging_body
        and label not in {"skirt", "miniskirt"}
        and float(skirt_hit["confidence"]) < 0.70
    ):
        skirt_hit = None
    if pants_hit is not None:
        if sneakers_hit is not None and not hanging_body:
            if extras:
                sneakers_hit["items"] = extras
            return sneakers_hit
        if heels_hit is not None and not hanging_body:
            if extras:
                heels_hit["items"] = extras
            return heels_hit
        prefer_skirt = (
            skirt_hit is not None
            and (
                label in {"skirt", "miniskirt"}
                or float(skirt_hit["confidence"])
                >= float(pants_hit["confidence"]) + 0.04
            )
            and not (label in {"shorts"} or fp_shorts >= fp_skirt + 0.06)
        )
        if prefer_skirt:
            lowerwear_tie = lowerwear_classifier.classify_lowerwear(
                image,
                whole_frame=isolated and not hanging_body,
            )
            if (
                lowerwear_tie is not None
                and not lowerwear_tie.get("usedFallback")
                and lowerwear_tie.get("subcategory") == "shorts"
            ):
                prefer_skirt = False
            elif fp_shorts >= 0.35 and fp_shorts >= fp_skirt:
                prefer_skirt = False
        if prefer_skirt:
            pants_hit = None
    if pants_hit is not None:
        locked_trousers = pants_hit
        lowerwear = lowerwear_classifier.classify_lowerwear(
            image,
            whole_frame=isolated and not hanging_body,
        )
        shorts_score = _ranked_score(lowerwear, "shorts")
        trousers_score = max(
            _ranked_score(lowerwear, "trousers"),
            _ranked_score(lowerwear, "jeans"),
        )
        # Keep real shorts. Do not accept skirt here — that head turns
        # hanging pants into a panel skirt, which is the bug we are fixing.
        if (
            lowerwear is not None
            and not lowerwear.get("usedFallback")
            and lowerwear.get("subcategory") == "shorts"
            and (
                (
                    shorts_score >= trousers_score + 0.08
                    and shorts_score >= 0.42
                )
                or (fp_shorts >= 0.32 and fp_shorts >= fp_skirt)
            )
        ):
            if extras:
                lowerwear["items"] = extras
            return lowerwear
        if (
            lowerwear is not None
            and not lowerwear.get("usedFallback")
            and lowerwear.get("subcategory") in {"trousers", "jeans"}
        ):
            if extras:
                lowerwear["items"] = extras
            return lowerwear
        if extras:
            locked_trousers["items"] = extras
        return locked_trousers

    # Skirt vs belt vs hat. Hat and belt modules are unchanged; this only
    # runs when those heads did not already return.
    if skirt_hit is not None:
        dress_gate = dress_upperwear_gate.classify_dress_vs_upperwear(image)
        silhouette = None
        if hanging_body or fp_dress >= 0.28 or (dress_gate or {}).get("preferDress"):
            silhouette = silhouette_classifier.classify_silhouette(image)
        if (
            silhouette is not None
            and not silhouette.get("usedFallback")
            and silhouette.get("subcategory") == "dress"
            and fp_shorts < 0.40
        ):
            if extras:
                silhouette["items"] = extras
            return silhouette
        if (
            (dress_gate or {}).get("preferDress")
            and float((dress_gate or {}).get("confidence") or 0) >= 0.55
            and fp_shorts < 0.35
        ):
            return _as_dress(
                float(dress_gate["confidence"]), extras, source="dress_upperwear_gate"
            )
        if fp_dress >= 0.35 and fp_dress >= fp_skirt and fp_dress >= fp_shorts:
            return _as_dress(fp_dress, extras, source="fashionpedia")
        lowerwear = lowerwear_classifier.classify_lowerwear(
            image,
            whole_frame=isolated and not hanging_body,
        )
        if (
            lowerwear is not None
            and not lowerwear.get("usedFallback")
            and lowerwear.get("subcategory") == "shorts"
            and (
                _ranked_score(lowerwear, "shorts") >= 0.42
                or fp_shorts >= fp_skirt
            )
        ):
            if extras:
                lowerwear["items"] = extras
            return lowerwear
        if fp_shorts >= 0.35 and fp_shorts >= fp_skirt + 0.04:
            if (
                lowerwear is not None
                and not lowerwear.get("usedFallback")
                and lowerwear.get("subcategory") == "shorts"
            ):
                if extras:
                    lowerwear["items"] = extras
                return lowerwear
        if (
            lowerwear is not None
            and not lowerwear.get("usedFallback")
            and lowerwear.get("subcategory") == "skirt"
        ):
            if extras:
                lowerwear["items"] = extras
            return lowerwear
        if extras:
            skirt_hit["items"] = extras
        return skirt_hit

    # Shirt vs dupatta vs hat. Accessory and lowerwear modules are unchanged.
    if shirt_hit is not None:
        if extras:
            shirt_hit["items"] = extras
        return shirt_hit

    def _topwear_hint() -> float:
        return max((_ranked_score(chosen, n) for n in _TOPWEAR_HINTS), default=0.0)

    def _try_upperwear(*, allow_soft: bool = False) -> dict[str, Any] | None:
        """Shirt / t-shirt / hoodie / jacket / top / dress. Never trousers."""
        garment = garment_classifier.classify_garment(image)
        if garment is None:
            return None
        sub = garment.get("subcategory")
        conf = float(garment.get("confidence") or 0)
        ranked = garment.get("ranked") or []
        allowed = {"shirt", "t-shirt", "hoodie", "jacket", "top", "dress", "coat"}
        if sub not in allowed and ranked:
            top = ranked[0] if isinstance(ranked[0], dict) else None
            if top and top.get("subcategory") in allowed:
                sub = top["subcategory"]
                conf = float(top.get("confidence") or conf)
        if sub not in allowed:
            return None

        def _gscore(name: str) -> float:
            for row in ranked:
                if isinstance(row, dict) and row.get("subcategory") == name:
                    return float(row.get("confidence") or 0)
            return 0.0

        jacket_score = _gscore("jacket")
        shirt_score = _gscore("shirt")
        tshirt_score = _gscore("t-shirt")
        inet_jacket = label in _JACKET_HINTS or _ranked_score(chosen, "jacket") >= 0.06
        if sub not in {"dress", "hoodie", "top"}:
            if (
                inet_jacket
                and jacket_score >= 0.22
                and jacket_score + 0.03 >= shirt_score
                and jacket_score + 0.02 >= tshirt_score
            ):
                sub, conf = "jacket", jacket_score
            elif (
                sub == "shirt"
                and jacket_score >= conf - 0.05
                and jacket_score >= 0.30
                and inet_jacket
            ):
                sub, conf = "jacket", jacket_score

        second = 0.0
        if len(ranked) > 1 and isinstance(ranked[1], dict):
            second = float(ranked[1].get("confidence") or 0)
        if garment.get("usedFallback") and sub != "jacket":
            if not allow_soft:
                return None
            # Soft: only with shirt-like ImageNet AND a clear top score.
            if conf < 0.45 or (conf - second) < 0.08:
                return None
        display = {
            "shirt": "Shirt",
            "t-shirt": "T-shirt",
            "jacket": "Jacket",
            "hoodie": "Hoodie",
            "top": "Top",
            "dress": "Dress",
            "coat": "Coat",
        }.get(sub, sub)
        out = dict(garment)
        out["usedFallback"] = False
        out["category"] = "dress" if sub in {"dress", "gown"} else "upperwear"
        out["subcategory"] = sub
        out["confidence"] = conf
        out["displayName"] = display
        out["message"] = f"Detected {display} ({conf * 100:.0f}%)."
        if extras:
            out["items"] = extras
        return out

    def _try_footwear(hint: dict[str, Any] | None) -> dict[str, Any] | None:
        sub = (hint or {}).get("subcategory")
        if not footwear_classifier.should_override(sub) and sub not in FOOTWEAR:
            return None
        if sub in FOOTWEAR and not footwear_classifier.should_override(sub):
            out = dict(hint or {})
            if extras:
                out["items"] = extras
            return out
        refined = footwear_classifier.classify_footwear(image, imagenet_hint=hint)
        if refined is not None and not refined.get("usedFallback"):
            out = dict(refined)
            if extras:
                out["items"] = extras
            return out
        return None

    def _try_footwear_forced() -> dict[str, Any] | None:
        """Run footwear4 even when ImageNet/accessory said bag/hat/unknown.

        Isolated heels are frequently bag in the 4-class accessory head
        (shoes→bag collision). The hint must not block the specialist.
        """
        if bag_gate.looks_like_bag(image):
            return None
        hint = chosen if label in FOOTWEAR else {
            "subcategory": "unknown",
            "confidence": 0.0,
        }
        refined = footwear_classifier.classify_footwear(image, imagenet_hint=hint)
        if refined is None or refined.get("usedFallback"):
            return None
        if refined.get("subcategory") not in FOOTWEAR:
            return None
        out = dict(refined)
        if extras:
            out["items"] = extras
        return out

    # Resolve known footwear BEFORE upperwear — heel product shots often
    # trip hanging_body geometry and were rewritten to jacket/t-shirt.
    # On a table-top product shot, ImageNet often calls a tote a loafer.
    # Run the accessory head first so a bag is not locked as shoes.
    if label in FOOTWEAR and not (isolated and not hanging_body):
        hit = _try_footwear(chosen)
        if hit is not None:
            return hit
        if chosen is not None:
            return chosen

    shirt_like = label in _SHIRT_LIKE | {
        "coat",
        "hoodie",
        "blazer",
        "sweater",
        "cardigan",
    }
    # Prefer upperwear for hanging shirts and shirt-like ImageNet — but not
    # before accessory on isolated unknowns (heels/caps share that geometry).
    upperwear_candidate = (shirt_like and not _has_strong_bag_hint(chosen)) or (
        hanging_body and label in {"hat", "unknown"} and not isolated
    )

    # Isolated footwear is decided after the accessory head (see below).
    if upperwear_candidate and shirt_like and label not in FOOTWEAR:
        early_upper = _try_upperwear()
        if early_upper is not None:
            return early_upper

    # Isolated caps are ImageNet-unknown (no baseball-cap class) and
    # sometimes swimming_trunks. Always run the 4-class head then — the
    # trousers/shorts/skirt head has no hat class.
    need_accessory = (
        accessory_classifier.should_override(label)
        or isolated
        or label in _ISOLATED_LOWERWEAR
        or label in FOOTWEAR
    )
    # Run the bag/hat/skirt/shoes specialist BEFORE any ImageNet hat
    # early-return. Isolated backpacks are often cowboy_hat; hanging
    # totes are often miniskirt. Those must not skip this head.
    if need_accessory:
        accessory = accessory_classifier.classify_accessory(
            image, imagenet_hint=chosen
        )
        accessory_label = (accessory or {}).get("subcategory")
        confident = (
            accessory is not None and not accessory.get("usedFallback")
        )
        hat_score = _ranked_score(accessory, "hat")
        bag_score = _ranked_score(accessory, "bag")
        skirt_score = _ranked_score(accessory, "skirt")
        shoes_score = _ranked_score(accessory, "shoes")
        if (
            confident
            and accessory_label in accessory_classifier.TRUE_ACCESSORIES
        ):
            acc_conf = float(accessory.get("confidence") or 0)
            compact_accessory = accessory_label in {
                "bag",
                "hat",
                "sunglasses",
                "belt",
                "jewelry",
            }
            steal_hat_from_shirt = (
                hanging_body and shirt_like and accessory_label == "hat"
            )
            if not steal_hat_from_shirt and (
                isolated
                or (compact_accessory and acc_conf >= 0.48)
            ):
                if accessory_label == "bag":
                    hit = _try_footwear_forced()
                    if hit is not None:
                        fconf = float(hit.get("confidence") or 0)
                        if fconf >= 0.78 and fconf >= acc_conf + 0.18:
                            return hit
                if extras:
                    accessory["items"] = extras
                return accessory
        if confident and accessory_label == "bag":
            # Isolated heels/sneakers often win as Bag in this 4-class head.
            # Always try footwear4 on isolated product shots before locking Bag.
            rival = max(hat_score, skirt_score)
            if shoes_score >= 0.10:
                hit = _try_footwear_forced()
                if hit is not None:
                    fconf = float(hit.get("confidence") or 0)
                    if fconf >= 0.78 and fconf >= bag_score + 0.18:
                        return hit
            # Never lock bag on a hanging shirt/jacket crop — but keep a
            # confident tote (bag_score high) instead of rewriting to jacket.
            if (hanging_body or shirt_like) and bag_score < 0.30:
                early_upper = _try_upperwear(allow_soft=True)
                if early_upper is not None:
                    return early_upper
            gate = dress_upperwear_gate.classify_dress_vs_upperwear(image)
            # Only steal Bag when the bag score is weak and the gate is sure.
            if (
                gate is not None
                and gate.get("preferUpperwear")
                and bag_score < 0.32
            ):
                early_upper = _try_upperwear(allow_soft=True)
                if early_upper is not None:
                    return early_upper
            skip_bag = bool(gate and gate.get("preferDress") and bag_score < 0.40)
            if isolated and shoes_score < 0.05:
                skip_bag = False
            if not hanging_body and not skip_bag:
                two_class_hat = (
                    label == "hat"
                    and isolated
                    and not _has_strong_bag_hint(chosen)
                    and "hat" not in accessory_classifier.status().get("classes", [])
                )
                keep_bag = (not isolated) or _has_strong_bag_hint(chosen) or (
                    hat_score < 0.20 or bag_score >= hat_score + 0.12
                )
                # Bags must stay bags unless hat clearly dominates (bag→hat fix).
                prefer_hat = (
                    isolated
                    and hat_score >= 0.20
                    and hat_score >= bag_score + 0.08
                    and bag_score < 0.36
                    and not _has_strong_bag_hint(chosen)
                    and _topwear_hint() < 0.08
                )
                if prefer_hat:
                    return _as_hat(accessory, extras, hat_score)
                if not two_class_hat and keep_bag and not shirt_like:
                    if extras:
                        accessory["items"] = extras
                    return accessory
        # Accessory pooled "shoes" → footwear4. Do not steal caps:
        # only when ImageNet agrees, or shoes clearly beats hat/bag.
        if confident and accessory_label in FOOTWEAR:
            trust_shoes = label in FOOTWEAR or (
                isolated
                and not hanging_body
                and not shirt_like
                and shoes_score >= bag_score
                and shoes_score >= hat_score + 0.06
            )
            if trust_shoes:
                hit = _try_footwear(
                    chosen if label in FOOTWEAR else accessory
                )
                if hit is not None and hit.get("subcategory") in FOOTWEAR:
                    return hit
                forced = _try_footwear_forced()
                if forced is not None:
                    return forced
        isolated_shoes = confident and accessory_label in FOOTWEAR and isolated
        # A table-top cap is often shoes in the 4-class head. Keep shoes
        # only when ImageNet also mapped the crop to footwear.
        if isolated_shoes and label in FOOTWEAR:
            hit = _try_footwear(chosen)
            if hit is not None:
                return hit
            if extras:
                accessory["items"] = extras
            return accessory
        # Hanging shirts/trousers must not early-return as hat — the
        # bag/hat/skirt/shoes head has no shirt class.
        # ImageNet often maps beanies to swimming_trunks/shorts; still
        # accept a confident accessory hat on isolated product shots.
        isolated_hat = (
            confident
            and accessory_label == "hat"
            and isolated
            and not hanging_body
            and label not in _SHIRT_LIKE
            and not shirt_like
            and _topwear_hint() < 0.08
        )
        if isolated_hat and not _has_strong_bag_hint(chosen):
            # Only steal hat→top when ImageNet clearly says jersey/shirt.
            if _topwear_hint() >= 0.12:
                early_upper = _try_upperwear(allow_soft=True)
                if (
                    early_upper is not None
                    and float(early_upper.get("confidence") or 0) >= 0.50
                ):
                    return early_upper
            if extras:
                accessory["items"] = extras
            return accessory
        # Top-down caps are ImageNet-unknown. If hat is competitive with
        # bag/skirt/shoes, do not send the crop to dress/shorts — even
        # when ImageNet already said shorts.
        if (
            isolated
            and accessory is not None
            and not _has_strong_bag_hint(chosen)
            and not hanging_body
            and label not in _SHIRT_LIKE
            and not shirt_like
            and _topwear_hint() < 0.10
        ):
            if (
                hat_score >= 0.12
                and hat_score + 0.08 >= bag_score
                and hat_score + 0.06 >= skirt_score
                and hat_score + 0.06 >= shoes_score
            ):
                # Hat vs shorts: lock hat before lowerwear on compact products.
                return _as_hat(accessory, extras, hat_score)
        # Isolated product: if shoes is competitive, refine to heels/flats/…
        # (heels rarely appear as an ImageNet class).
        if (
            isolated
            and accessory is not None
            and not hanging_body
            and not shirt_like
            and shoes_score >= 0.16
            and shoes_score + 0.02 >= hat_score
            and shoes_score + 0.02 >= bag_score
        ):
            hit = _try_footwear_forced()
            if hit is not None and hit.get("subcategory") in FOOTWEAR:
                return hit
            hit = _try_footwear(accessory)
            if hit is not None and hit.get("subcategory") in FOOTWEAR:
                return hit
        # Heels→jacket: when bag/hat are weak but footwear4 is sure, prefer shoes
        # even if the 4-class head did not pick "shoes" as the top label.
        if (
            isolated
            and accessory is not None
            and not hanging_body
            and not shirt_like
            and bag_score < 0.28
            and hat_score < 0.22
            and skirt_score < 0.28
            and _topwear_hint() < 0.08
        ):
            hit = _try_footwear_forced()
            if hit is not None and float(hit.get("confidence") or 0) >= 0.55:
                return hit
        if chosen is not None and chosen.get("subcategory") == "jewelry":
            return chosen
        if (
            chosen is not None
            and chosen.get("subcategory") == "belt"
            and not (confident and accessory_label == "bag")
        ):
            return chosen

    # Hanging shirt ImageNet-hat only — do not run upperwear on every
    # hanging unknown (pants/dresses share that geometry).
    if hanging_body and label == "hat":
        early_upper = _try_upperwear(allow_soft=False)
        if early_upper is not None:
            return early_upper
    if hanging_body and label == "unknown" and shirt_like:
        early_upper = _try_upperwear(allow_soft=True)
        if early_upper is not None:
            return early_upper

    safe_accessories = {
        "sunglasses",
        "watch",
        "scarf",
        "hijab",
        "dupatta",
    }
    if chosen is not None and chosen.get("subcategory") in safe_accessories:
        if chosen.get("subcategory") != "unknown" and not chosen.get("usedFallback"):
            return chosen
        if float(chosen.get("confidence") or 0) >= 0.22:
            return chosen
    # Isolated ImageNet hat only after the specialist declined Bag —
    # never for hanging shirts/trousers (cowboy_hat collision).
    # Never lock hat when jersey/t-shirt/shirt evidence is present.
    if (
        chosen is not None
        and chosen.get("subcategory") == "hat"
        and isolated
        and not hanging_body
        and not _has_bag_hint(chosen)
    ):
        # t-shirt→hat: only unlock hat when topwear evidence is present.
        if _topwear_hint() >= 0.10:
            early_upper = _try_upperwear(allow_soft=True)
            if early_upper is not None:
                return early_upper
        elif _topwear_hint() < 0.06:
            if chosen.get("subcategory") != "unknown" and not chosen.get("usedFallback"):
                return chosen
            if float(chosen.get("confidence") or 0) >= 0.22:
                return chosen
        if chosen.get("subcategory") != "unknown" and not chosen.get("usedFallback"):
            return chosen
        if float(chosen.get("confidence") or 0) >= 0.22:
            return chosen
    if chosen is not None and chosen.get("subcategory") in ACCESSORY_CLASSES:
        skip_on_tall = chosen.get("subcategory") in {
            "jewelry",
            "accessories",
            "hat",
        }
        if isolated and chosen.get("subcategory") == "bag" and accessory is not None:
            hat_score = _ranked_score(accessory, "hat")
            bag_score = _ranked_score(accessory, "bag")
            if (
                not hanging_body
                and hat_score >= 0.24
                and hat_score >= bag_score + 0.14
                and bag_score < 0.30
            ):
                return _as_hat(accessory, extras, hat_score)
        # Tall outfit frames may show a hat at the top — do not let that
        # beat the dress. A cropped beanie filling a portrait frame is
        # not an outfit; isolated is true for those.
        # Hanging body garments that ImageNet called hat must continue
        # to silhouette / lowerwear / finetuned instead of locking hat.
        if hanging_body and chosen.get("subcategory") == "hat":
            pass
        elif not ((not isolated) and skip_on_tall):
            if chosen.get("subcategory") != "unknown" and not chosen.get("usedFallback"):
                return chosen
            if float(chosen.get("confidence") or 0) >= 0.22:
                return chosen
    # Isolated shoe shots stay shoes. On a tall frame, shoes at the hem
    # must not beat a one-piece dress — check the full uncropped image first.
    tall = is_full_length_frame(image)
    # Never route shirt/t-shirt/blouse into the dress/skirt/trousers head —
    # that head has no upperwear classes and turns tops into Dress.
    onepiece_labels = {
        "dress",
        "gown",
        "modest dress",
        "skirt",
        "miniskirt",
        "trousers",
        "jeans",
        "unknown",
        "hat",
    }
    # A hanging tote is tall. Do not send it to dress/skirt/trousers —
    # that head has no bag class and will emit skirt.
    if label == "bag":
        if isolated and accessory is not None and not hanging_body:
            hat_score = _ranked_score(accessory, "hat")
            bag_score = _ranked_score(accessory, "bag")
            # Require a clear hat margin so bags do not become hats.
            if (
                hat_score >= 0.24
                and hat_score >= bag_score + 0.14
                and bag_score < 0.30
            ):
                return _as_hat(accessory, extras, hat_score)
        if chosen is not None:
            return chosen
    # Shirt-like labels: upperwear specialist before any dress/silhouette path.
    if shirt_like or label in _SHIRT_LIKE:
        early_upper = _try_upperwear(allow_soft=True)
        if early_upper is not None:
            return early_upper
    # Footwear must never enter the dress/silhouette head (heels→dress fix).
    # Only when the accessory head says shoes — do not run footwear4 on
    # every isolated top (sneakers path itself is unchanged).
    if label not in FOOTWEAR and accessory is not None:
        shoes_s = _ranked_score(accessory, "shoes")
        if shoes_s >= 0.16 and shoes_s + 0.02 >= _ranked_score(accessory, "hat") and shoes_s + 0.02 >= _ranked_score(accessory, "bag"):
            hit = _try_footwear_forced()
            if hit is not None and hit.get("subcategory") in FOOTWEAR:
                return hit
    # Isolated product shots (cap on a table) must not go to the
    # dress/skirt/trousers head — that head has no hat class.
    need_onepiece = (
        heels_hit is None
        and sneakers_hit is None
        and shoes_hit is None
        and flats_hit is None
        and fp_shoe < 0.40
        and label != "bag"
        and label not in _SHIRT_LIKE
        and not shirt_like
        and label not in FOOTWEAR
        and not (isolated and label in {"unknown", "hat", "belt"} and not hanging_body)
        and (
            silhouette_classifier.should_override(label)
            or (hanging_body and label not in _SHIRT_LIKE and label not in FOOTWEAR)
            or (hanging_body and fp_dress >= 0.28)
            # FOOTWEAR deliberately excluded: tall heel/sandal crops must not
            # become dress. Sneaker path is unchanged (resolved earlier).
            or (tall and label in onepiece_labels | {"hat"})
        )
    )
    if need_onepiece:
        silhouette = silhouette_classifier.classify_silhouette(image)
        if silhouette is not None and not silhouette.get("usedFallback"):
            extras = (chosen or {}).get("items") or []
            if silhouette.get("subcategory") == "dress":
                if shoes_hit is not None:
                    if extras:
                        shoes_hit["items"] = extras
                    return shoes_hit
                if heels_hit is not None:
                    if extras:
                        heels_hit["items"] = extras
                    return heels_hit
                # Tops / hanging shirts must not stay as Dress.
                if shirt_like:
                    early_upper = _try_upperwear(allow_soft=True)
                    if early_upper is not None:
                        return early_upper
                    if chosen is not None and label in _SHIRT_LIKE:
                        out = dict(chosen)
                        if extras:
                            out["items"] = extras
                        return out
                gate = dress_upperwear_gate.classify_dress_vs_upperwear(image)
                if gate is not None and gate.get("preferUpperwear"):
                    early_upper = _try_upperwear(allow_soft=True)
                    if early_upper is not None:
                        return early_upper
                elif hanging_body and (gate is None or not gate.get("preferDress")):
                    early_upper = _try_upperwear(allow_soft=False)
                    if (
                        early_upper is not None
                        and float(early_upper.get("confidence") or 0) >= 0.55
                    ):
                        return early_upper
                # If gate says dress, keep silhouette dress (do not soft-steal).
                if gate is not None and gate.get("preferDress"):
                    pass
                elif (
                    gate is not None
                    and not gate.get("preferDress")
                    and not gate.get("preferUpperwear")
                ):
                    early_upper = _try_upperwear(allow_soft=False)
                    if (
                        early_upper is not None
                        and float(early_upper.get("confidence") or 0) >= 0.65
                    ):
                        return early_upper
                # This head has no two-leg class. Laid-flat pants look like
                # a column and must not become Dress.
                lowerwear = lowerwear_classifier.classify_lowerwear(image)
                pants = _pants_from_lowerwear(lowerwear)
                if pants is not None:
                    if extras:
                        pants["items"] = extras
                    return pants
                # ImageNet already called this trousers/jeans. Do not
                # rewrite that as a one-piece.
                if label in _PANTS_LABELS and chosen is not None:
                    if extras:
                        chosen = dict(chosen)
                        chosen["items"] = extras
                    return chosen
                # Hanging shirt: dress head has no shirt class. Prefer a
                # jersey/t-shirt/shirt ImageNet hit, else leave for later.
                if hanging_body and label in _SHIRT_LIKE and chosen is not None:
                    if extras:
                        chosen = dict(chosen)
                        chosen["items"] = extras
                    return chosen
                if isolated and not hanging_body:
                    if (
                        lowerwear is not None
                        and not lowerwear.get("usedFallback")
                    ):
                        if extras:
                            lowerwear["items"] = extras
                        return lowerwear
                    # Do not return Dress for a table-top garment.
                elif extras:
                    silhouette["items"] = extras
                    return silhouette
                else:
                    return silhouette
            if silhouette.get("subcategory") in {"trousers", "skirt", "jeans"}:
                # Caps often become skirt/shorts — prefer accessory hat.
                if (
                    isolated
                    and not hanging_body
                    and accessory is not None
                    and _ranked_score(accessory, "hat") >= 0.14
                    and _ranked_score(accessory, "hat")
                    >= _ranked_score(accessory, "skirt") - 0.02
                ):
                    return _as_hat(
                        accessory, extras, _ranked_score(accessory, "hat")
                    )
                early_upper = _try_upperwear()
                if early_upper is not None and hanging_body and shirt_like:
                    return early_upper
                lowerwear = lowerwear_classifier.classify_lowerwear(image)
                if lowerwear is not None and not lowerwear.get("usedFallback"):
                    if extras:
                        lowerwear["items"] = extras
                    return lowerwear
                if extras:
                    silhouette["items"] = extras
                return silhouette
    if (
        hanging_body
        and fp_dress >= 0.40
        and heels_hit is None
        and shoes_hit is None
        and flats_hit is None
        and sneakers_hit is None
        and fp_shoe < 0.35
        and label not in FOOTWEAR
        and label not in {"hat", "watch", "belt", "bag", "dupatta"}
    ):
        gate = dress_upperwear_gate.classify_dress_vs_upperwear(image)
        if gate is None or not gate.get("preferUpperwear"):
            return _as_dress(fp_dress, extras, source="fashionpedia")
    if chosen is not None and chosen.get("subcategory") in FOOTWEAR:
        # Refine pooled "shoes" into flats / sneakers / heels / sandals.
        # should_override is False for heels when footwear3 (no heels class).
        sub = chosen.get("subcategory")
        if footwear_classifier.should_override(sub):
            refined = footwear_classifier.classify_footwear(
                image, imagenet_hint=chosen
            )
            if refined is not None and not refined.get("usedFallback"):
                extras = (chosen or {}).get("items") or []
                if extras:
                    refined = dict(refined)
                    refined["items"] = extras
                return refined
        return chosen
    # Isolated product shots (cap on a table) must not go to
    # trousers/shorts/skirt — that head has no hat class and emits shorts.
    accessory_hat = (
        accessory is not None
        and _ranked_score(accessory, "hat") >= 0.11
        and _ranked_score(accessory, "hat")
        >= _ranked_score(accessory, "bag") - 0.04
    )
    # Isolated heels must not fall through to jacket via garment should_override.
    # Only when the accessory head already prefers shoes over hat/bag.
    if (
        isolated
        and not hanging_body
        and not shirt_like
        and accessory is not None
        and _ranked_score(accessory, "shoes") >= 0.18
        and _ranked_score(accessory, "shoes")
        >= _ranked_score(accessory, "hat") + 0.02
        and _ranked_score(accessory, "shoes")
        >= _ranked_score(accessory, "bag")
    ):
        foot = _try_footwear_forced()
        if foot is not None and float(foot.get("confidence") or 0) >= 0.40:
            return foot
    if accessory_hat and accessory is not None and isolated and not hanging_body and _topwear_hint() < 0.10:
        return _as_hat(accessory, extras, _ranked_score(accessory, "hat"))
    # Upperwear specialist: shirt / t-shirt / hoodie / jacket / top / dress.
    if (
        not upperwear_candidate
        and not accessory_hat
        and (
            garment_classifier.should_override(label)
            or (hanging_body and label in {"hat", "unknown"})
        )
    ):
        early_upper = _try_upperwear()
        if early_upper is not None:
            return early_upper
    skip_lowerwear = (
        isolated
        and not hanging_body
        and (
            label in {"hat", "belt"}
            or accessory_hat
            # ImageNet swimming_trunks / shorts on a beanie: never trust
            # the lowerwear head for compact table-top products.
            or (
                label in _PANTS_LABELS
                and accessory is not None
                and _ranked_score(accessory, "hat") >= 0.08
            )
            or (
                label in {"unknown", "shorts"}
                and accessory is not None
                and _ranked_score(accessory, "hat") >= 0.10
                and _ranked_score(accessory, "hat")
                >= _ranked_score(accessory, "skirt")
            )
        )
    )
    # Always try lowerwear for hanging pants-like crops and ImageNet pants.
    if (
        (lowerwear_classifier.should_override(label) or hanging_body or label in _PANTS_LABELS)
        and not skip_lowerwear
    ):
        lowerwear = lowerwear_classifier.classify_lowerwear(
            image,
            whole_frame=isolated and not hanging_body,
        )
        if lowerwear is not None and not lowerwear.get("usedFallback"):
            extras = (chosen or {}).get("items") or []
            # Isolated table-top: shorts from a cropped hat must not win.
            if (
                isolated
                and not hanging_body
                and accessory_hat
                and lowerwear.get("subcategory") in _PANTS_LABELS | {"skirt"}
            ):
                return _as_hat(
                    accessory,
                    extras,
                    _ranked_score(accessory, "hat"),
                )
            if extras:
                lowerwear["items"] = extras
            return lowerwear
        pants = _pants_from_lowerwear(lowerwear)
        if pants is not None:
            extras = (chosen or {}).get("items") or []
            if extras:
                pants["items"] = extras
            return pants
    # Hanging shirt with ImageNet hat/unknown: map to shirt when jersey/
    # pajama appeared in ranked scores, else prefer finetuned/shirt guess.
    if hanging_body and chosen is not None:
        if chosen.get("subcategory") in _SHIRT_LIKE:
            return chosen
        if chosen.get("subcategory") in _PANTS_LABELS:
            return chosen
        shirt_rank = max(
            (_ranked_score(chosen, name) for name in _SHIRT_LIKE),
            default=0.0,
        )
        # Finetuned may carry shirt even when ImageNet preferred hat.
        if finetuned is not None and finetuned.get("subcategory") in _SHIRT_LIKE:
            if not finetuned.get("usedFallback") or float(finetuned.get("confidence") or 0) >= 0.28:
                return finetuned
        if shirt_rank >= 0.06:
            out = dict(chosen)
            best_shirt = max(
                (
                    (name, _ranked_score(chosen, name))
                    for name in _SHIRT_LIKE
                ),
                key=lambda row: row[1],
            )[0]
            out["subcategory"] = best_shirt
            out["category"] = "upperwear"
            out["usedFallback"] = False
            out["displayName"] = best_shirt.replace("-", " ").title()
            out["message"] = f"Detected {best_shirt} (hanging garment)."
            return out
        # Last resort for hanging torso panels: upperwear beats cowboy_hat.
        # Prefer jacket when the specialist ranks it; else shirt (not hat).
        if chosen.get("subcategory") == "hat":
            early_upper = _try_upperwear(allow_soft=False)
            if early_upper is not None:
                return early_upper
            return _result(
                "shirt",
                max(float(chosen.get("confidence") or 0.35), 0.42),
                False,
                chosen.get("source") or "imagenet",
                "Detected shirt (hanging garment; hat collision suppressed).",
                extras or None,
            )
    if chosen is not None:
        if isolated and not hanging_body and accessory is not None:
            hat_score = _ranked_score(accessory, "hat")
            skirt_score = _ranked_score(accessory, "skirt")
            bag_score = _ranked_score(accessory, "bag")
            # Beanie / cap: ImageNet swimming_trunks or lowerwear shorts must
            # not beat a competitive accessory hat on the full frame.
            if (
                hat_score >= 0.12
                and hat_score + 0.08 >= bag_score
                and label in _PANTS_LABELS | {"unknown", "skirt", "miniskirt"}
            ):
                return _as_hat(accessory, extras, hat_score)
            if label in _ISOLATED_LOWERWEAR:
                if hat_score >= 0.14 and hat_score + 0.10 >= skirt_score:
                    return _as_hat(accessory, extras, hat_score)
                # ImageNet miniskirt on a cap must not win just because
                # the 4-class head also has a skirt class.
                if label in {"skirt", "miniskirt"} and (
                    skirt_score < hat_score + 0.12
                ):
                    if hat_score >= 0.12:
                        return _as_hat(accessory, extras, hat_score)
        return chosen
    return _result(
        "unknown",
        0.0,
        True,
        "none",
        "MobileNetV2 is not installed and no fine-tuned model was found. "
        "Select the type manually.",
    )


def _prefer_accessory(
    imagenet: dict[str, Any] | None,
    finetuned: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Use the local ImageNet MobileNetV2 for accessories; otherwise the fine-tuned head."""
    inet_label = (imagenet or {}).get("subcategory")
    fine_label = (finetuned or {}).get("subcategory")
    # Never let a weak ImageNet hat beat a fine-tuned shirt/trousers head.
    if (
        finetuned is not None
        and fine_label in (_SHIRT_LIKE | _PANTS_LABELS)
        and not finetuned.get("usedFallback")
        and inet_label in {"hat", "bag", "jewelry", "accessories", "unknown"}
    ):
        return finetuned
    inet_acc = (
        imagenet is not None
        and imagenet.get("subcategory") in ACCESSORY_CLASSES
        and imagenet.get("subcategory") != "unknown"
    )
    if inet_acc and not imagenet.get("usedFallback"):
        # Fine-tuned body garment still wins over ImageNet accessory noise.
        if (
            finetuned is not None
            and fine_label in (_SHIRT_LIKE | _PANTS_LABELS | {"dress", "gown", "skirt"})
            and not finetuned.get("usedFallback")
            and float(finetuned.get("confidence") or 0) >= 0.34
        ):
            return finetuned
        return imagenet
    if inet_acc and float(imagenet.get("confidence") or 0) >= 0.22:
        fine_is_body = finetuned is None or finetuned.get("subcategory") not in ACCESSORY_CLASSES
        if fine_is_body:
            imagenet["usedFallback"] = False
            imagenet["message"] = (
                f'Detected {imagenet["subcategory"]} with ImageNet MobileNetV2.'
            )
            return imagenet
    if finetuned is not None:
        return finetuned
    return imagenet


def _classify_finetuned(image: Image.Image) -> dict[str, Any]:
    batch = preprocess_mobilenet_v2(image)
    probs = np.asarray(_finetuned.predict(batch, verbose=0))[0]
    ranked = sorted(
        (
            (_finetuned_labels[i] if i < len(_finetuned_labels) else f"class_{i}", float(p))
            for i, p in enumerate(probs)
        ),
        key=lambda row: row[1],
        reverse=True,
    )
    label, confidence, uncertain, message = apply_family_constraints(ranked)
    extras = extra_items(ranked, label)
    if extras:
        names = ", ".join(f"{row['subcategory']} ({float(row['confidence']) * 100:.0f}%)" for row in extras)
        message = f"{message} Other visible items: {names}."
    return _result(label, confidence, uncertain, "finetuned", message, extras, ranked[:5])


def _lookup(label: str) -> tuple[str, str] | None:
    key = (label or "").strip()
    spaced = key.replace("_", " ")
    underscored = key.replace(" ", "_")
    return (
        IMAGENET_TO_CLOTHING.get(key)
        or IMAGENET_TO_CLOTHING.get(spaced)
        or IMAGENET_TO_CLOTHING.get(underscored)
        or IMAGENET_TO_CLOTHING.get(key.lower())
        or IMAGENET_TO_CLOTHING.get(spaced.lower())
    )


SKIRT_HINT_NAMES = {
    "miniskirt",
    "mini skirt",
    "hoopskirt",
    "hoop skirt",
    "overskirt",
    "over skirt",
    "sarong",
}

HAT_HINT_NAMES = {
    "bonnet",
    "bathing cap",
    "shower cap",
    "sombrero",
    "cowboy hat",
    "bearskin",
    "pickelhaube",
    "mortarboard",
    "crash helmet",
    "football helmet",
    "ski mask",
}

BAG_HINT_NAMES = {
    "backpack",
    "purse",
    "mailbag",
    "mail bag",
    "plastic bag",
    "shopping basket",
    "suitcase",
    "wallet",
    "packet",
    "hamper",
    "pencil box",
    "pencil_box",
}

JEWELRY_HINT_NAMES = {
    "necklace",
    "chain",
    "hair slide",
    "bolo tie",
    "bow tie",
    "windsor tie",
}


def _norm_name(label: str) -> str:
    return (label or "").replace("_", " ").strip().lower()


def _from_imagenet_pairs(pairs: list[tuple[str, float]]) -> dict[str, Any]:
    pooled: dict[str, float] = {}
    wool = 0.0
    hat_hint = 0.0
    skirt_hint = 0.0
    bag_hint = 0.0
    jewelry_hint = 0.0
    for name, score in pairs:
        key = _norm_name(name)
        if key == "wool":
            wool += float(score)
        if key in HAT_HINT_NAMES:
            hat_hint += float(score)
        if key in SKIRT_HINT_NAMES:
            skirt_hint += float(score)
        if key in BAG_HINT_NAMES:
            bag_hint += float(score)
        if key in JEWELRY_HINT_NAMES:
            jewelry_hint += float(score)
        hit = _lookup(name)
        if not hit:
            continue
        pooled[hit[1]] = pooled.get(hit[1], 0.0) + float(score)
    if (
        wool >= 0.10
        and (pooled.get("hat", 0.0) > 0.0 or hat_hint >= 0.04)
        and skirt_hint < 0.04
        and pooled.get("bag", 0.0) < 0.08
        and max((pooled.get(name, 0.0) for name in UPPERWEAR_KEEP), default=0.0) < 0.06
        and max(
            (
                pooled.get("jeans", 0.0),
                pooled.get("trousers", 0.0),
                pooled.get("shorts", 0.0),
            ),
            default=0.0,
        )
        < 0.06
    ):
        pooled["hat"] = pooled.get("hat", 0.0) + wool
    mapped = sorted(pooled.items(), key=lambda row: row[1], reverse=True)
    raw_top = float(pairs[0][1]) if pairs else 0.0
    if not mapped:
        top = pairs[0][0] if pairs else "unknown"
        return _result(
            "unknown",
            raw_top,
            True,
            "imagenet",
            f'Top ImageNet class was "{top}", which is not a clothing item. '
            "Please select the type manually.",
        )
    hat_score = pooled.get("hat", 0.0)
    bag_score = pooled.get("bag", 0.0)
    jewelry_score = pooled.get("jewelry", 0.0)
    belt_score = pooled.get("belt", 0.0)
    skirt_score = pooled.get("skirt", 0.0)
    jeans_score = pooled.get("jeans", 0.0)
    trousers_score = pooled.get("trousers", 0.0)
    shorts_score = pooled.get("shorts", 0.0)
    pants_score = max(jeans_score, trousers_score, shorts_score)
    shirt_score = max((pooled.get(name, 0.0) for name in UPPERWEAR_KEEP), default=0.0)
    dress_score = pooled.get("dress", 0.0) + pooled.get("gown", 0.0)
    foot_score = max((pooled.get(name, 0.0) for name in (
        "heels", "shoes", "sneakers", "flats", "boots", "sandals", "loafers",
    )), default=0.0)
    # ImageNet gown/academic_gown collides with laid-flat pants. If jean
    # or trousers is in the top classes, that is the garment — never keep
    # a one-piece over it.
    if pants_score >= 0.06 and pants_score >= dress_score * 0.28:
        pants_label = max(
            (
                ("jeans", jeans_score),
                ("trousers", trousers_score),
                ("shorts", shorts_score),
            ),
            key=lambda row: row[1],
        )[0]
        mapped = [(pants_label, pants_score)] + [
            row for row in mapped if row[0] != pants_label
        ]
    # Prefer shirt/t-shirt over a weak cowboy_hat collision.
    if shirt_score >= 0.05 and shirt_score + 0.01 >= hat_score:
        shirt_label = max(
            ((name, pooled.get(name, 0.0)) for name in UPPERWEAR_KEEP),
            key=lambda row: row[1],
        )[0]
        if pooled.get(shirt_label, 0.0) >= 0.05:
            mapped = [(shirt_label, pooled[shirt_label])] + [
                row for row in mapped if row[0] != shirt_label
            ]
    # Chain/necklace is an ImageNet class collision on handbags, not a
    # garment-structure guess. Do not promote skirt here — that overwrote
    # shorts, trousers, dresses, and bags.
    if bag_score >= 0.05 and jewelry_score > 0 and (
        bag_score >= jewelry_score * 0.40 or bag_hint >= 0.04
    ):
        mapped = [("bag", bag_score)] + [
            row for row in mapped if row[0] != "bag"
        ]
    elif bag_score >= 0.04 and belt_score > 0 and (
        bag_score >= belt_score * 0.28 or bag_hint >= 0.04
    ):
        mapped = [("bag", bag_score)] + [
            row for row in mapped if row[0] != "bag"
        ]
    elif (
        bag_score >= 0.08
        and bag_score >= hat_score
        and bag_score >= max(skirt_score, foot_score, 0.0) * 0.28
    ):
        mapped = [("bag", bag_score)] + [
            row for row in mapped if row[0] != "bag"
        ]
    elif (
        hat_score >= 0.12
        and hat_score >= foot_score * 0.35
        and hat_score >= bag_score
        and hat_score >= skirt_score
        and hat_score >= shirt_score + 0.04
        and hat_score >= pants_score + 0.04
    ):
        mapped = [("hat", hat_score)] + [
            row for row in mapped if row[0] != "hat"
        ]
    label, confidence, uncertain, message = apply_family_constraints(mapped)
    best_name, best_score = mapped[0]
    if (
        uncertain
        and best_name in ACCESSORY_CLASSES
        and best_score >= 0.08
        and best_score >= raw_top * 0.35
    ):
        label, confidence, uncertain = best_name, best_score, False
        message = f"Detected {label} with ImageNet MobileNetV2."
    # Only true footwear may be rewritten to bag/hat — never jeans/trousers.
    if label in FOOTWEAR:
        if bag_score >= 0.06 and bag_score >= hat_score:
            label, confidence, uncertain = "bag", bag_score, False
            message = "Detected bag with ImageNet MobileNetV2."
        elif hat_score >= 0.12 and hat_score >= shirt_score and hat_score >= pants_score:
            label, confidence, uncertain = "hat", hat_score, False
            message = "Detected hat with ImageNet MobileNetV2."
    extras = extra_items(mapped, label)
    if label in ACCESSORY_CLASSES and not uncertain:
        message = f"Detected {label} with ImageNet MobileNetV2."
    return _result(label, confidence, uncertain, "imagenet", message, extras, mapped[:5])


def _classify_imagenet(image: Image.Image) -> dict[str, Any] | None:
    if _imagenet_backend.startswith("tensorflow") or _imagenet_backend.startswith("keras"):
        return _classify_imagenet_tf(image)
    if _imagenet_backend == "torch":
        return _classify_imagenet_torch(image)
    return None


def _classify_imagenet_tf(image: Image.Image) -> dict[str, Any]:
    batch = preprocess_mobilenet_v2(image)
    preds = _imagenet.predict(batch, verbose=0)
    decoded = _imagenet_decode(preds, top=15)[0]
    return _from_imagenet_pairs([(label, float(conf)) for _id, label, conf in decoded])


def _classify_imagenet_torch(image: Image.Image) -> dict[str, Any]:
    import torch

    model, weights = _imagenet
    tensor = weights.transforms()(image).unsqueeze(0)
    with torch.no_grad():
        logits = model(tensor)
        probs = torch.softmax(logits, dim=1)[0]
    top = torch.topk(probs, k=15)
    categories = weights.meta["categories"]
    pairs = [
        (categories[idx], float(conf))
        for idx, conf in zip(top.indices.tolist(), top.values.tolist())
    ]
    return _from_imagenet_pairs(pairs)


def _result(
    subcategory: str,
    confidence: float,
    uncertain: bool,
    source: str,
    message: str,
    items: list[dict[str, object]] | None = None,
    ranked: list[tuple[str, float]] | None = None,
) -> dict[str, Any]:
    if subcategory == "unknown":
        category = "accessories"
    else:
        category = CLASS_TO_CATEGORY.get(subcategory, family_of(subcategory))
    return {
        "category": category,
        "subcategory": subcategory,
        "confidence": float(confidence),
        "usedFallback": uncertain,
        "source": source,
        "message": message,
        "items": items or [],
        "ranked": [
            {"subcategory": name, "confidence": score} for name, score in (ranked or [])
        ],
    }
