"""Skirt vs belt vs hat gate.

A hanging or laid-flat skirt is a single textile panel, so hat_gate calls
it a hat and the belt head calls it a belt. This specialist is trained
only on those three leaves. If it says skirt, the wardrobe label is
``lowerwear / skirt``. Accessory gates and trousers_gate are not modified.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .clothing_taxonomy import letterbox_mobilenet_v2

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_PATH = MODELS_DIR / "skirt_gate_mobilenetv2.keras"
LABELS_PATH = MODELS_DIR / "skirt_gate_labels.json"
CLASS_ORDER = ("skirt", "belt", "hat")
DISPLAY = {"skirt": "Skirt", "belt": "Belt", "hat": "Hat"}

MIN_SKIRT = 0.38
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


def classify_skirt_gate(image: Image.Image) -> dict[str, Any] | None:
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
        "skirt": scores.get("skirt", 0.0),
        "belt": scores.get("belt", 0.0),
        "hat": scores.get("hat", 0.0),
        "ranked": ranked,
    }


def lock_skirt(image: Image.Image) -> dict[str, Any] | None:
    gate = classify_skirt_gate(image)
    if gate is None:
        return None
    skirt = float(gate["skirt"])
    belt = float(gate["belt"])
    hat = float(gate["hat"])
    if skirt < MIN_SKIRT:
        return None
    if skirt < belt + MIN_MARGIN:
        return None
    if skirt < hat + MIN_MARGIN:
        return None
    return _as_skirt(gate)


def lock_or_prefer_skirt(image: Image.Image) -> dict[str, Any] | None:
    """One forward pass: prefer first, then lock."""
    gate = classify_skirt_gate(image)
    if gate is None:
        return None
    skirt = float(gate["skirt"])
    belt = float(gate["belt"])
    hat = float(gate["hat"])
    if (
        skirt >= 0.45
        and belt <= 0.28
        and hat <= 0.28
        and skirt >= belt + MIN_MARGIN
        and skirt >= hat + MIN_MARGIN
    ):
        return _as_skirt(gate)
    if skirt < MIN_SKIRT:
        return None
    if skirt < belt + 0.04:
        return None
    if skirt < hat + 0.04:
        return None
    return _as_skirt(gate)


def prefer_skirt_over_hat(image: Image.Image) -> dict[str, Any] | None:
    """hat_gate and belt heads have no skirt class."""
    gate = classify_skirt_gate(image)
    if gate is None:
        return None
    skirt = float(gate["skirt"])
    belt = float(gate["belt"])
    hat = float(gate["hat"])
    if skirt < 0.45:
        return None
    if hat > 0.28:
        return None
    if belt > 0.28:
        return None
    if skirt < hat + MIN_MARGIN:
        return None
    if skirt < belt + MIN_MARGIN:
        return None
    return _as_skirt(gate)


def _as_skirt(gate: dict[str, Any]) -> dict[str, Any]:
    skirt = float(gate["skirt"])
    return {
        "category": "lowerwear",
        "subcategory": "skirt",
        "confidence": skirt,
        "usedFallback": False,
        "source": "skirt_gate",
        "message": f"Detected Skirt ({skirt * 100:.0f}%).",
        "displayName": "Skirt",
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
        _error = "skirt_gate_mobilenetv2.keras is missing."
        return
    try:
        from tensorflow.keras.models import load_model

        _model = load_model(MODEL_PATH)
    except Exception as exc:  # noqa: BLE001
        _error = str(exc)
        _model = None
