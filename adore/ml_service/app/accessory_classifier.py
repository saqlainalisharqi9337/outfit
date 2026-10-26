"""8-class accessory specialist (Fashionpedia + open images).

Previous bag/hat/skirt/shoes head treated skirt as a rival class, so a tote
could legally win as Skirt. This head only predicts accessories:

    bag, belt, scarf, dupatta, hat, hijab, jewelry, sunglasses

Shoes and skirts stay on their own specialists. Trained by
``train_accessories.py`` from Fashionpedia crops and Wikimedia Commons.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .clothing_taxonomy import CLASS_TO_CATEGORY, letterbox_mobilenet_v2, preprocess_mobilenet_v2
from .fashionpedia_map import ACCESSORY_LEAVES

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_CANDIDATES = (
    MODELS_DIR / "accessories8_mobilenetv2.keras",
    MODELS_DIR / "accessories8_mobilenetv2.h5",
    MODELS_DIR / "bag_shoes_mobilenetv2.keras",
    MODELS_DIR / "bag_shoes_mobilenetv2.h5",
)
LABELS_CANDIDATES = (
    MODELS_DIR / "accessories8_labels.json",
    MODELS_DIR / "bag_shoes_labels.json",
)

CLASS_ORDER = ACCESSORY_LEAVES
DISPLAY_NAME = {
    "bag": "Bag",
    "belt": "Belt",
    "scarf": "Scarf",
    "dupatta": "Dupatta",
    "hat": "Hat",
    "hijab": "Hijab",
    "jewelry": "Jewellery",
    "sunglasses": "Sunglasses",
    "watch": "Watch",
    "skirt": "Skirt",
    "shoes": "Shoes",
}

TRUE_ACCESSORIES = set(ACCESSORY_LEAVES) | {"watch"}

CONFUSED_LABELS = {
    "bag",
    "purse",
    "handbag",
    "backpack",
    "tote",
    "clutch",
    "wallet",
    "shoulder bag",
    "crossbody",
    "sling bag",
    "sling",
    "messenger",
    "satchel",
    "bucket bag",
    "duffel",
    "hat",
    "cap",
    "beanie",
    "cowboy_hat",
    "sombrero",
    "bonnet",
    "miniskirt",
    "mini skirt",
    "overskirt",
    "hoopskirt",
    "skirt",
    "dress",
    "gown",
    "jumpsuit",
    "unknown",
    "belt",
    "buckle",
    "scarf",
    "stole",
    "dupatta",
    "hijab",
    "jewelry",
    "necklace",
    "sunglasses",
    "sunglass",
    "glasses",
    "watch",
}

MIN_CONFIDENCE = 0.38
MIN_GAP = 0.06

_model = None
_labels: list[str] = list(CLASS_ORDER)
_loaded = False
_model_mtime = 0.0
_error = ""
_min_confidence = MIN_CONFIDENCE
_min_gap = MIN_GAP
_letterbox = True


def status() -> dict[str, Any]:
    _ensure_loaded()
    return {
        "loaded": _model is not None,
        "classes": list(_labels),
        "minConfidence": _min_confidence,
        "minGap": _min_gap,
        "error": _error,
        "trueAccessories": sorted(TRUE_ACCESSORIES),
    }


def should_override(label: str | None) -> bool:
    return (label or "unknown") in CONFUSED_LABELS


def classify_accessory(
    image: Image.Image,
    imagenet_hint: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    _ensure_loaded()
    if _model is None:
        return None
    batch = (
        letterbox_mobilenet_v2(image) if _letterbox else preprocess_mobilenet_v2(image)
    )
    probs = np.asarray(_model.predict(batch, verbose=0))[0]
    n = min(len(_labels), len(probs))
    ranked = sorted(
        ((_labels[i], float(probs[i])) for i in range(n)),
        key=lambda row: row[1],
        reverse=True,
    )
    if not ranked:
        return None
    label, confidence = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0.0
    gap = confidence - second
    # Legacy 4-class weights may still emit skirt/shoes. Never surface those
    # as an accessory decision — that is what mapped bags to skirts.
    if label not in TRUE_ACCESSORIES:
        return _uncertain(ranked, confidence)
    if confidence < _min_confidence or gap < _min_gap:
        return _uncertain(ranked, confidence)
    display = DISPLAY_NAME.get(label, label)
    return {
        "category": CLASS_TO_CATEGORY.get(label, "accessories"),
        "subcategory": label,
        "confidence": float(confidence),
        "usedFallback": False,
        "source": "accessory",
        "message": f"Detected {display} ({confidence * 100:.0f}%).",
        "displayName": display,
        "items": [],
        "ranked": [
            {
                "subcategory": name,
                "displayName": DISPLAY_NAME.get(name, name),
                "confidence": score,
            }
            for name, score in ranked
        ],
    }


def _uncertain(ranked: list[tuple[str, float]], confidence: float) -> dict[str, Any]:
    return {
        "category": "accessories",
        "subcategory": "unknown",
        "confidence": float(confidence),
        "usedFallback": True,
        "source": "accessory",
        "message": "Uncertain accessory type. Please select bag, hat, scarf, or jewellery.",
        "displayName": "Unknown/Uncertain",
        "items": [],
        "ranked": [
            {
                "subcategory": name,
                "displayName": DISPLAY_NAME.get(name, name),
                "confidence": score,
            }
            for name, score in ranked
        ],
    }


def _weights_mtime() -> float:
    stamps = [path.stat().st_mtime for path in MODEL_CANDIDATES if path.is_file()]
    for labels in LABELS_CANDIDATES:
        if labels.is_file():
            stamps.append(labels.stat().st_mtime)
    return max(stamps) if stamps else 0.0


def _ensure_loaded() -> None:
    global _loaded, _model, _labels, _error, _min_confidence, _min_gap, _model_mtime
    global _letterbox
    newest = _weights_mtime()
    if _loaded and _model is not None and newest <= _model_mtime:
        return
    previous = _model
    _loaded = True
    for labels_path in LABELS_CANDIDATES:
        if not labels_path.is_file():
            continue
        try:
            payload = json.loads(labels_path.read_text(encoding="utf-8"))
            classes = list(payload.get("classes") or [])
            if len(classes) >= 2:
                _labels = classes
            uncertain = payload.get("uncertain") or {}
            _min_confidence = float(uncertain.get("min_confidence", MIN_CONFIDENCE))
            _min_gap = float(uncertain.get("min_gap", MIN_GAP))
            _letterbox = "letterbox" in str(payload.get("preprocess") or "") or True
            break
        except json.JSONDecodeError as exc:
            _error = f"{labels_path.name} is invalid: {exc}"
    for path in MODEL_CANDIDATES:
        if not path.is_file():
            continue
        try:
            from tensorflow.keras.models import load_model

            loaded = load_model(path)
            units = int(loaded.output_shape[-1])
            if len(_labels) != units:
                _labels = [f"class_{i}" for i in range(units)]
            _model = loaded
            _model_mtime = newest
            _error = ""
            return
        except Exception as exc:  # noqa: BLE001
            _error = f"{path.name}: {exc}"
            _model = previous
            if previous is not None:
                return
