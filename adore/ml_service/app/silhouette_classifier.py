"""3-class MobileNetV2: long dress vs pants vs long skirt.

Trained by `train_dress_pants_skirt.py`. Same 224 RGB preprocess as
ImageNet MobileNetV2: x / 127.5 - 1.

Wardrobe labels (stable index order):
    0 dress      Long Dress
    1 skirt      Long Skirt
    2 trousers   Pants/Trousers  (jeans in the dataset are this class)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .clothing_taxonomy import CLASS_TO_CATEGORY, preprocess_mobilenet_v2

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_CANDIDATES = (
    MODELS_DIR / "dress_pants_skirt_mobilenetv2.keras",
    MODELS_DIR / "dress_pants_skirt_mobilenetv2.h5",
)
LABELS_PATH = MODELS_DIR / "dress_pants_skirt_labels.json"

# Fixed mapping used in training and inference. Do not sort at load time.
CLASS_ORDER = ("dress", "skirt", "trousers")
DISPLAY_NAME = {
    "dress": "Dress",
    "skirt": "Skirt",
    "trousers": "Trousers/Pants",
}
CONFUSED_LABELS = {
    "dress",
    "gown",
    "modest dress",
    "skirt",
    "miniskirt",
    "trousers",
    "jeans",
    "unknown",
}

MIN_CONFIDENCE = 0.42
MIN_GAP = 0.08

_model = None
_labels: list[str] = list(CLASS_ORDER)
_loaded = False
_error = ""


def status() -> dict[str, Any]:
    _ensure_loaded()
    return {
        "loaded": _model is not None,
        "classes": list(_labels),
        "error": _error,
    }


def should_override(label: str | None) -> bool:
    return (label or "unknown") in CONFUSED_LABELS


def classify_silhouette(image: Image.Image) -> dict[str, Any] | None:
    _ensure_loaded()
    if _model is None:
        return None
    batch = preprocess_mobilenet_v2(image)
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
    if confidence < MIN_CONFIDENCE or gap < MIN_GAP:
        return {
            "category": "accessories",
            "subcategory": "unknown",
            "confidence": float(confidence),
            "usedFallback": True,
            "source": "silhouette",
            "message": (
                "Uncertain between long dress, pants, and long skirt. "
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
        "source": "silhouette",
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


def _ensure_loaded() -> None:
    global _loaded, _model, _labels, _error
    if _loaded:
        return
    _loaded = True
    if LABELS_PATH.is_file():
        try:
            payload = json.loads(LABELS_PATH.read_text(encoding="utf-8"))
            classes = list(payload.get("classes") or [])
            if len(classes) == 3:
                _labels = classes
        except json.JSONDecodeError as exc:
            _error = f"dress_pants_skirt_labels.json is invalid: {exc}"
    for path in MODEL_CANDIDATES:
        if not path.is_file():
            continue
        try:
            from tensorflow.keras.models import load_model

            _model = load_model(path)
            units = int(_model.output_shape[-1])
            if len(_labels) != units:
                _labels = [f"class_{i}" for i in range(units)]
            return
        except Exception as exc:  # noqa: BLE001
            _error = f"{path.name}: {exc}"
            _model = None
