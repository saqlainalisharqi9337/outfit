"""Binary shirt detector.

Previous 3/4-class gates still lost hanging and worn shirts to hat, dupatta,
and one-piece dress because those heads run first and softmax splits the
shirt score. This specialist only answers: shirt vs not-shirt.

If it says shirt, the wardrobe label is ``upperwear / shirt``. Accessory
and lowerwear gate modules are not modified.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .clothing_taxonomy import letterbox_mobilenet_v2

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_PATH = MODELS_DIR / "shirt_detector_mobilenetv2.keras"
LABELS_PATH = MODELS_DIR / "shirt_detector_labels.json"
CLASS_ORDER = ("shirt", "other")
DISPLAY = {"shirt": "Shirt", "other": "Other"}

# High recall: a shirt must not fall through to hat/dupatta/dress.
MIN_SHIRT = 0.46

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


def classify_shirt_gate(image: Image.Image) -> dict[str, Any] | None:
    _ensure_loaded()
    if _model is None:
        return None
    batch = letterbox_mobilenet_v2(image)
    probs = np.asarray(_model.predict(batch, verbose=0))[0]
    n = min(len(_labels), len(probs))
    ranked = sorted(
        ((_labels[i], float(probs[i])) for i in range(n)),
        key=lambda row: row[1],
        reverse=True,
    )
    if not ranked:
        return None
    scores = {name: score for name, score in ranked}
    return {
        "subcategory": ranked[0][0],
        "confidence": ranked[0][1],
        "shirt": scores.get("shirt", 0.0),
        "other": scores.get("other", 0.0),
        "dupatta": 0.0,
        "hat": 0.0,
        "dress": 0.0,
        "ranked": ranked,
    }


def lock_shirt(image: Image.Image) -> dict[str, Any] | None:
    gate = classify_shirt_gate(image)
    if gate is None:
        return None
    return _lock_from_gate(gate)


def lock_or_prefer_shirt(
    image: Image.Image,
    *,
    hanging: bool = False,
) -> dict[str, Any] | None:
    """Return upperwear/shirt when the binary head says it is a shirt."""
    del hanging
    gate = classify_shirt_gate(image)
    if gate is None:
        return None
    return _lock_from_gate(gate)


def _lock_from_gate(gate: dict[str, Any]) -> dict[str, Any] | None:
    shirt = float(gate["shirt"])
    other = float(gate.get("other") or 0.0)
    if shirt < MIN_SHIRT:
        return None
    if shirt < other:
        return None
    return _as_shirt(gate)


def _as_shirt(gate: dict[str, Any]) -> dict[str, Any]:
    shirt = float(gate["shirt"])
    return {
        "category": "upperwear",
        "subcategory": "shirt",
        "confidence": shirt,
        "usedFallback": False,
        "source": "shirt_gate",
        "message": f"Detected Shirt ({shirt * 100:.0f}%).",
        "displayName": "Shirt",
        "items": [],
        "ranked": [
            {
                "subcategory": name,
                "displayName": DISPLAY.get(name, name),
                "confidence": score,
            }
            for name, score in gate["ranked"]
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
            if classes == list(CLASS_ORDER) or set(classes) == set(CLASS_ORDER):
                _labels = classes
        except json.JSONDecodeError as exc:
            _error = str(exc)
    if not MODEL_PATH.is_file():
        _error = "shirt_detector_mobilenetv2.keras is missing."
        return
    try:
        from tensorflow.keras.models import load_model

        _model = load_model(MODEL_PATH)
        units = int(_model.output_shape[-1])
        if len(_labels) != units:
            _labels = list(CLASS_ORDER)[:units]
    except Exception as exc:  # noqa: BLE001
        _error = str(exc)
        _model = None
