"""Hat vs bag vs shirt gate.

A cap is a compact accessory, so ImageNet and the upperwear head call it a
shirt, and the bag gate / accessory head sometimes call it a bag. This
specialist is trained only on those three leaves. If it says hat, the
wardrobe label is ``accessories / hat``. Bags already locked by bag_gate
must not be rewritten here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .clothing_taxonomy import letterbox_mobilenet_v2

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_PATH = MODELS_DIR / "hat_gate_mobilenetv2.keras"
LABELS_PATH = MODELS_DIR / "hat_gate_labels.json"
CLASS_ORDER = ("hat", "bag", "shirt")
DISPLAY = {"hat": "Hat", "bag": "Bag", "shirt": "Shirt"}

MIN_HAT = 0.38
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


def classify_hat_gate(image: Image.Image) -> dict[str, Any] | None:
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
        "hat": scores.get("hat", 0.0),
        "bag": scores.get("bag", 0.0),
        "shirt": scores.get("shirt", 0.0),
        "ranked": ranked,
    }


def lock_hat(image: Image.Image) -> dict[str, Any] | None:
    """Return an accessories/hat result when the gate is sure it is a hat."""
    gate = classify_hat_gate(image)
    if gate is None:
        return None
    hat = float(gate["hat"])
    bag = float(gate["bag"])
    shirt = float(gate["shirt"])
    if hat < MIN_HAT:
        return None
    if hat < bag + MIN_MARGIN:
        return None
    if hat < shirt + MIN_MARGIN:
        return None
    return _as_hat(gate)


def prefer_hat_over_bag(image: Image.Image) -> dict[str, Any] | None:
    """bag_gate has no hat class, so a cap often locks as bag.

    Rewrite only when this head is sure it is a hat and its own bag score
    is low. Real bags stay bags.
    """
    gate = classify_hat_gate(image)
    if gate is None:
        return None
    hat = float(gate["hat"])
    bag = float(gate["bag"])
    shirt = float(gate["shirt"])
    if hat < 0.48:
        return None
    if bag > 0.28:
        return None
    if hat < shirt + MIN_MARGIN:
        return None
    return _as_hat(gate)


def _as_hat(gate: dict[str, Any]) -> dict[str, Any]:
    hat = float(gate["hat"])
    return {
        "category": "accessories",
        "subcategory": "hat",
        "confidence": hat,
        "usedFallback": False,
        "source": "hat_gate",
        "message": f"Detected Hat ({hat * 100:.0f}%).",
        "displayName": "Hat",
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
        _error = "hat_gate_mobilenetv2.keras is missing."
        return
    try:
        from tensorflow.keras.models import load_model

        _model = load_model(MODEL_PATH)
    except Exception as exc:  # noqa: BLE001
        _error = str(exc)
        _model = None
