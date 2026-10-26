"""Watch vs bag vs trousers gate.

A wristwatch is a small rectangle, so bag_gate calls it a bag and the
trousers head calls it trousers. This specialist is trained only on those
three leaves. If it says watch, the wardrobe label is ``accessories / watch``.
Bag and hat gates are not modified.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .clothing_taxonomy import letterbox_mobilenet_v2

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_PATH = MODELS_DIR / "watch_gate_mobilenetv2.keras"
LABELS_PATH = MODELS_DIR / "watch_gate_labels.json"
CLASS_ORDER = ("watch", "bag", "trousers")
DISPLAY = {"watch": "Watch", "bag": "Bag", "trousers": "Trousers"}

MIN_WATCH = 0.38
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


def classify_watch_gate(image: Image.Image) -> dict[str, Any] | None:
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
        "watch": scores.get("watch", 0.0),
        "bag": scores.get("bag", 0.0),
        "trousers": scores.get("trousers", 0.0),
        "ranked": ranked,
    }


def lock_watch(image: Image.Image) -> dict[str, Any] | None:
    gate = classify_watch_gate(image)
    if gate is None:
        return None
    watch = float(gate["watch"])
    bag = float(gate["bag"])
    trousers = float(gate["trousers"])
    if watch < MIN_WATCH:
        return None
    if watch < bag + MIN_MARGIN:
        return None
    if watch < trousers + MIN_MARGIN:
        return None
    return _as_watch(gate)


def prefer_watch_over_bag(image: Image.Image) -> dict[str, Any] | None:
    """bag_gate has no watch class, so a watch often locks as bag."""
    gate = classify_watch_gate(image)
    if gate is None:
        return None
    watch = float(gate["watch"])
    bag = float(gate["bag"])
    trousers = float(gate["trousers"])
    if watch < 0.45:
        return None
    if bag > 0.32:
        return None
    if watch < trousers + MIN_MARGIN:
        return None
    return _as_watch(gate)


def _as_watch(gate: dict[str, Any]) -> dict[str, Any]:
    watch = float(gate["watch"])
    return {
        "category": "accessories",
        "subcategory": "watch",
        "confidence": watch,
        "usedFallback": False,
        "source": "watch_gate",
        "message": f"Detected Watch ({watch * 100:.0f}%).",
        "displayName": "Watch",
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
        _error = "watch_gate_mobilenetv2.keras is missing."
        return
    try:
        from tensorflow.keras.models import load_model

        _model = load_model(MODEL_PATH)
    except Exception as exc:  # noqa: BLE001
        _error = str(exc)
        _model = None
