"""Watch vs belt vs bag vs trousers gate.

A wristwatch is a small rectangle, so bag_gate and the trousers head call it
a bag or trousers. A belt is a long strap, so it becomes a bag or another
garment. This specialist is trained only on those four leaves. If it says
watch or belt, the wardrobe label is ``accessories / watch`` or
``accessories / belt``. Bag and hat gates are not modified.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .clothing_taxonomy import letterbox_mobilenet_v2

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_PATH = MODELS_DIR / "watch_belt_gate_mobilenetv2.keras"
LABELS_PATH = MODELS_DIR / "watch_belt_gate_labels.json"
CLASS_ORDER = ("watch", "belt", "bag", "trousers")
DISPLAY = {
    "watch": "Watch",
    "belt": "Belt",
    "bag": "Bag",
    "trousers": "Trousers",
}

MIN_LOCK = 0.38
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


def classify_watch_belt(image: Image.Image) -> dict[str, Any] | None:
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
        "belt": scores.get("belt", 0.0),
        "bag": scores.get("bag", 0.0),
        "trousers": scores.get("trousers", 0.0),
        "ranked": ranked,
    }


def lock_watch(image: Image.Image) -> dict[str, Any] | None:
    return _lock(image, "watch")


def lock_belt(image: Image.Image) -> dict[str, Any] | None:
    return _lock(image, "belt")


def prefer_watch_over_bag(image: Image.Image) -> dict[str, Any] | None:
    """bag_gate has no watch class, so a watch often locks as bag."""
    return _prefer(image, "watch")


def prefer_belt_over_bag(image: Image.Image) -> dict[str, Any] | None:
    """bag_gate has no belt class, so a belt often locks as bag."""
    return _prefer(image, "belt")


def _lock(image: Image.Image, leaf: str) -> dict[str, Any] | None:
    gate = classify_watch_belt(image)
    if gate is None:
        return None
    score = float(gate[leaf])
    if score < MIN_LOCK:
        return None
    rivals = [name for name in CLASS_ORDER if name != leaf]
    if leaf == "watch" and float(gate["belt"]) > 0.22:
        return None
    if any(score < float(gate[name]) + MIN_MARGIN for name in rivals):
        return None
    return _as_item(gate, leaf)


def _prefer(image: Image.Image, leaf: str) -> dict[str, Any] | None:
    gate = classify_watch_belt(image)
    if gate is None:
        return None
    score = float(gate[leaf])
    bag = float(gate["bag"])
    trousers = float(gate["trousers"])
    other = float(gate["belt" if leaf == "watch" else "watch"])
    if score < 0.48:
        return None
    if bag > 0.28:
        return None
    if leaf == "watch" and other > 0.22:
        return None
    if score < trousers + MIN_MARGIN:
        return None
    if score < other + MIN_MARGIN:
        return None
    return _as_item(gate, leaf)


def _as_item(gate: dict[str, Any], leaf: str) -> dict[str, Any]:
    score = float(gate[leaf])
    return {
        "category": "accessories",
        "subcategory": leaf,
        "confidence": score,
        "usedFallback": False,
        "source": "watch_belt_gate",
        "message": f"Detected {DISPLAY[leaf]} ({score * 100:.0f}%).",
        "displayName": DISPLAY[leaf],
        "items": [],
        "ranked": [
            {
                "subcategory": name,
                "displayName": DISPLAY.get(name, name),
                "confidence": value,
            }
            for name, value in gate["ranked"]
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
            if len(classes) == 4:
                _labels = classes
        except json.JSONDecodeError as exc:
            _error = str(exc)
    if not MODEL_PATH.is_file():
        _error = "watch_belt_gate_mobilenetv2.keras is missing."
        return
    try:
        from tensorflow.keras.models import load_model

        _model = load_model(MODEL_PATH)
    except Exception as exc:  # noqa: BLE001
        _error = str(exc)
        _model = None
