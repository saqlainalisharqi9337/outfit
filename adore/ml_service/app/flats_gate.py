"""Binary flats detector.

Hat_gate is hat/bag/shirt only, so a compact ballet flat looks more like a
hat than a bag or shirt. This head only answers: flats vs not-flats.

If it says flats, the wardrobe label is ``footwear / flats``. Hat, bag,
shirt, jacket, t-shirt, and lowerwear gate modules are not modified.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .clothing_taxonomy import letterbox_mobilenet_v2

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_PATH = MODELS_DIR / "flats_gate_mobilenetv2.keras"
LABELS_PATH = MODELS_DIR / "flats_gate_labels.json"
CLASS_ORDER = ("flats", "other")
DISPLAY = {"flats": "Flats", "other": "Other"}

# Precision vs hats: hat_gate already handles those.
MIN_FLATS = 0.56
MIN_HANGING = 0.50

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


def classify_flats_gate(image: Image.Image) -> dict[str, Any] | None:
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
        "flats": scores.get("flats", 0.0),
        "other": scores.get("other", 0.0),
        "ranked": ranked,
    }


def lock_flats(image: Image.Image) -> dict[str, Any] | None:
    gate = classify_flats_gate(image)
    if gate is None:
        return None
    return _lock_from_gate(gate)


def lock_or_prefer_flats(
    image: Image.Image,
    *,
    hanging: bool = False,
) -> dict[str, Any] | None:
    gate = classify_flats_gate(image)
    if gate is None:
        return None
    # Hanging shirts/jackets must not become flats. Compact product flats
    # are not hanging_body.
    if hanging:
        return None
    return _lock_from_gate(gate)


def _lock_from_gate(gate: dict[str, Any]) -> dict[str, Any] | None:
    flats = float(gate["flats"])
    other = float(gate.get("other") or 0.0)
    if flats < MIN_FLATS:
        return None
    if flats < other:
        return None
    return _as_flats(gate)


def _as_flats(gate: dict[str, Any]) -> dict[str, Any]:
    flats = float(gate["flats"])
    return {
        "category": "footwear",
        "subcategory": "flats",
        "confidence": flats,
        "usedFallback": False,
        "source": "flats_gate",
        "message": f"Detected Flats ({flats * 100:.0f}%).",
        "displayName": "Flats",
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
        _error = "flats_gate_mobilenetv2.keras is missing."
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
