"""Bag vs skirt vs flats gate.

A tote is a hanging rectangle, so ImageNet and the dress/skirt heads call it
a skirt, and the footwear head calls it flats. This specialist is trained
only on those three leaves. If it says bag, the wardrobe label is
``accessories / bag`` and skirt/flats must not override it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .clothing_taxonomy import letterbox_mobilenet_v2

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_PATH = MODELS_DIR / "bag_gate_mobilenetv2.keras"
LABELS_PATH = MODELS_DIR / "bag_gate_labels.json"
CLASS_ORDER = ("bag", "skirt", "flats")
DISPLAY = {"bag": "Bag", "skirt": "Skirt", "flats": "Flats"}

MIN_BAG = 0.38
MIN_MARGIN = 0.06

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


def classify_bag_gate(image: Image.Image) -> dict[str, Any] | None:
    """Raw 3-way scores. Does not decide wardrobe routing by itself."""
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
    label, confidence = ranked[0]
    scores = {name: score for name, score in ranked}
    return {
        "subcategory": label,
        "confidence": confidence,
        "bag": scores.get("bag", 0.0),
        "skirt": scores.get("skirt", 0.0),
        "flats": scores.get("flats", 0.0),
        "ranked": ranked,
    }


def looks_like_bag(image: Image.Image) -> bool:
    """True when bag is the gate winner. Used to veto skirt/flats specialists."""
    gate = classify_bag_gate(image)
    if gate is None:
        return False
    bag = float(gate["bag"])
    return (
        bag >= 0.34
        and bag >= float(gate["skirt"]) + 0.04
        and bag >= float(gate["flats"]) + 0.04
    )


def lock_bag(image: Image.Image) -> dict[str, Any] | None:
    """Return an accessories/bag result when the gate is sure it is a bag."""
    gate = classify_bag_gate(image)
    if gate is None:
        return None
    bag = float(gate["bag"])
    skirt = float(gate["skirt"])
    flats = float(gate["flats"])
    if bag < MIN_BAG:
        return None
    if bag < skirt + MIN_MARGIN:
        return None
    if bag < flats + MIN_MARGIN:
        return None
    return {
        "category": "accessories",
        "subcategory": "bag",
        "confidence": bag,
        "usedFallback": False,
        "source": "bag_gate",
        "message": f"Detected Bag ({bag * 100:.0f}%).",
        "displayName": "Bag",
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
            if len(classes) == 3:
                _labels = classes
        except json.JSONDecodeError as exc:
            _error = str(exc)
    if not MODEL_PATH.is_file():
        _error = "bag_gate_mobilenetv2.keras is missing."
        return
    try:
        from tensorflow.keras.models import load_model

        _model = load_model(MODEL_PATH)
    except Exception as exc:  # noqa: BLE001
        _error = str(exc)
        _model = None
