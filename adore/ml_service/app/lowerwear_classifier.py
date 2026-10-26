"""3-class MobileNetV2: trousers vs shorts vs skirt.

Trained by `train_trousers_shorts_skirt.py`. Same 224 RGB preprocess as
the rest of Adore: x / 127.5 - 1.

Fixed index order (training, export, and this module must match):
    0 trousers   Pants/Trousers  (jeans/palazzo/joggers live in pants/)
    1 shorts     Shorts
    2 skirt      Skirt

This head learns two-leg vs one-panel construction and leg length.
It does not invent palazzo/mini subfolders; those stay inside pants/shorts/skirt.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .clothing_taxonomy import (
    CLASS_TO_CATEGORY,
    emphasize_lower_body,
    lower_structure_crop,
    preprocess_mobilenet_v2,
)

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_CANDIDATES = (
    MODELS_DIR / "trousers_shorts_skirt_mobilenetv2.keras",
    MODELS_DIR / "trousers_shorts_skirt_mobilenetv2.h5",
)
LABELS_PATH = MODELS_DIR / "trousers_shorts_skirt_labels.json"

# Do not sort alphabetically at load time.
CLASS_ORDER = ("trousers", "shorts", "skirt")
DISPLAY_NAME = {
    "trousers": "Trousers/Pants",
    "shorts": "Shorts",
    "skirt": "Skirt",
}
CONFUSED_LABELS = {
    "trousers",
    "pants",
    "jeans",
    "shorts",
    "skirt",
    "miniskirt",
    "mini skirt",
    "hoopskirt",
    "overskirt",
    "palazzo",
    "chinos",
    "joggers",
    "unknown",
}

MIN_CONFIDENCE = 0.42
MIN_GAP = 0.08

_model = None
_labels: list[str] = list(CLASS_ORDER)
_loaded = False
_model_mtime = 0.0
_error = ""
_min_confidence = MIN_CONFIDENCE
_min_gap = MIN_GAP


def status() -> dict[str, Any]:
    _ensure_loaded()
    return {
        "loaded": _model is not None,
        "classes": list(_labels),
        "index": {name: i for i, name in enumerate(_labels)},
        "minConfidence": _min_confidence,
        "minGap": _min_gap,
        "error": _error,
    }


def should_override(label: str | None) -> bool:
    return (label or "unknown") in CONFUSED_LABELS


def classify_lowerwear(
    image: Image.Image,
    *,
    whole_frame: bool = False,
) -> dict[str, Any] | None:
    _ensure_loaded()
    if _model is None:
        return None
    # Table-top product shots: classify the whole garment, not a bottom crop
    # that turns beanies into shorts.
    if whole_frame:
        views = [image]
    else:
        views = [emphasize_lower_body(image), lower_structure_crop(image)]
    stacked = np.concatenate(
        [preprocess_mobilenet_v2(view) for view in views],
        axis=0,
    )
    probs = np.asarray(_model.predict(stacked, verbose=0)).mean(axis=0)
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
    if confidence < _min_confidence or gap < _min_gap:
        return {
            "category": "accessories",
            "subcategory": "unknown",
            "confidence": float(confidence),
            "usedFallback": True,
            "source": "lowerwear",
            "message": (
                "Uncertain between trousers, shorts, and skirt. "
                "Please select the type."
            ),
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
    display = DISPLAY_NAME.get(label, label)
    return {
        "category": CLASS_TO_CATEGORY.get(label, "lowerwear"),
        "subcategory": label,
        "confidence": float(confidence),
        "usedFallback": False,
        "source": "lowerwear",
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


def _weights_mtime() -> float:
    stamps = [path.stat().st_mtime for path in MODEL_CANDIDATES if path.is_file()]
    if LABELS_PATH.is_file():
        stamps.append(LABELS_PATH.stat().st_mtime)
    return max(stamps) if stamps else 0.0


def _ensure_loaded() -> None:
    global _loaded, _model, _labels, _error, _min_confidence, _min_gap, _model_mtime
    newest = _weights_mtime()
    if _loaded and _model is not None and newest <= _model_mtime:
        return
    previous = _model
    _loaded = True
    if LABELS_PATH.is_file():
        try:
            payload = json.loads(LABELS_PATH.read_text(encoding="utf-8"))
            classes = list(payload.get("classes") or [])
            if len(classes) == 3:
                _labels = classes
            uncertain = payload.get("uncertain") or {}
            _min_confidence = float(uncertain.get("min_confidence", MIN_CONFIDENCE))
            _min_gap = float(uncertain.get("min_gap", MIN_GAP))
        except json.JSONDecodeError as exc:
            _error = f"trousers_shorts_skirt_labels.json is invalid: {exc}"
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
