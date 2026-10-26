"""Trousers vs dress vs shirt gate.

Hanging pants look like a single textile column, so the silhouette head
calls them a one-piece dress and the shirt head calls them a shirt. This
specialist is trained only on those three leaves. If it says trousers,
the wardrobe label is ``lowerwear / trousers``. Accessory gates and the
existing trousers/shorts/skirt weights are not modified.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .clothing_taxonomy import letterbox_mobilenet_v2

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_PATH = MODELS_DIR / "trousers_gate_mobilenetv2.keras"
LABELS_PATH = MODELS_DIR / "trousers_gate_labels.json"
CLASS_ORDER = ("trousers", "dress", "shirt")
DISPLAY = {"trousers": "Trousers/Pants", "dress": "Dress", "shirt": "Shirt"}

MIN_TROUSERS = 0.38
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


def classify_trousers_gate(image: Image.Image) -> dict[str, Any] | None:
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
        "trousers": scores.get("trousers", 0.0),
        "dress": scores.get("dress", 0.0),
        "shirt": scores.get("shirt", 0.0),
        "ranked": ranked,
    }


def lock_trousers(image: Image.Image) -> dict[str, Any] | None:
    gate = classify_trousers_gate(image)
    if gate is None:
        return None
    trousers = float(gate["trousers"])
    dress = float(gate["dress"])
    shirt = float(gate["shirt"])
    if trousers < MIN_TROUSERS:
        return None
    if trousers < dress + MIN_MARGIN:
        return None
    # Shirt is the noisier negative; require a clearer gap so tops stay tops.
    if trousers < shirt + 0.10:
        return None
    return _as_trousers(gate)


def lock_or_prefer_trousers(image: Image.Image) -> dict[str, Any] | None:
    """One forward pass: prefer first, then lock."""
    gate = classify_trousers_gate(image)
    if gate is None:
        return None
    trousers = float(gate["trousers"])
    dress = float(gate["dress"])
    shirt = float(gate["shirt"])
    if (
        trousers >= 0.45
        and dress <= 0.32
        and shirt <= 0.28
        and trousers >= dress + MIN_MARGIN
        and trousers >= shirt + MIN_MARGIN
    ):
        return _as_trousers(gate)
    if trousers < MIN_TROUSERS:
        return None
    if trousers < dress + 0.04:
        return None
    if trousers < shirt + 0.04:
        return None
    return _as_trousers(gate)


def prefer_trousers_over_dress(image: Image.Image) -> dict[str, Any] | None:
    """Silhouette has no two-leg class, so pants often lock as dress or shirt."""
    gate = classify_trousers_gate(image)
    if gate is None:
        return None
    trousers = float(gate["trousers"])
    dress = float(gate["dress"])
    shirt = float(gate["shirt"])
    if trousers < 0.45:
        return None
    if dress > 0.32:
        return None
    if shirt > 0.28:
        return None
    if trousers < dress + MIN_MARGIN:
        return None
    if trousers < shirt + MIN_MARGIN:
        return None
    return _as_trousers(gate)


def _as_trousers(gate: dict[str, Any]) -> dict[str, Any]:
    trousers = float(gate["trousers"])
    return {
        "category": "lowerwear",
        "subcategory": "trousers",
        "confidence": trousers,
        "usedFallback": False,
        "source": "trousers_gate",
        "message": f"Detected Trousers/Pants ({trousers * 100:.0f}%).",
        "displayName": "Trousers/Pants",
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
        _error = "trousers_gate_mobilenetv2.keras is missing."
        return
    try:
        from tensorflow.keras.models import load_model

        _model = load_model(MODEL_PATH)
    except Exception as exc:  # noqa: BLE001
        _error = str(exc)
        _model = None
