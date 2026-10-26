"""Upperwear specialist: shirt / t-shirt / hoodie / jacket / top / dress.

Loads ``upperwear6_resnet18.pt`` when present, else the older 3-class
``upperwear3_resnet18.pt``. Never predicts trousers or skirts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

from .clothing_taxonomy import CLASS_TO_CATEGORY

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_CANDIDATES = (
    MODELS_DIR / "upperwear6_resnet18.pt",
    MODELS_DIR / "upperwear3_resnet18.pt",
    MODELS_DIR / "garment4_resnet18.pt",
)

UPPERWEAR_LABELS = frozenset(
    {"shirt", "t-shirt", "hoodie", "jacket", "top", "dress", "coat"}
)
DISPLAY_NAME = {
    "shirt": "Shirt",
    "t-shirt": "T-shirt",
    "hoodie": "Hoodie",
    "jacket": "Jacket",
    "top": "Top",
    "dress": "Dress",
    "coat": "Coat",
    "gown": "Gown",
}
CONFUSED_LABELS = {
    "shirt",
    "t-shirt",
    "jacket",
    "coat",
    "hoodie",
    "blazer",
    "sweater",
    "top",
    "blouse",
    "unknown",
}

MIN_CONFIDENCE = 0.36
MIN_GAP = 0.04

_model = None
_labels: list[str] = []
_loaded = False
_error = ""
_torch = None
_transform = None


def status() -> dict[str, Any]:
    _ensure_loaded()
    return {
        "loaded": _model is not None,
        "classes": list(_labels),
        "error": _error,
        "minConfidence": MIN_CONFIDENCE,
    }


def loaded_classes() -> list[str]:
    _ensure_loaded()
    return list(_labels)


def should_override(label: str | None) -> bool:
    return (label or "unknown") in CONFUSED_LABELS


def reset() -> None:
    """Force the next classify call to reload weights from disk."""
    global _model, _labels, _loaded, _error, _torch, _transform
    _model = None
    _labels = []
    _loaded = False
    _error = ""
    _torch = None
    _transform = None


def _ensure_loaded() -> None:
    global _model, _labels, _loaded, _error, _torch, _transform
    if _loaded:
        return
    _loaded = True
    try:
        import torch
        from torchvision import models, transforms
    except Exception as exc:  # noqa: BLE001
        _error = f"torch unavailable: {exc}"
        return

    ckpt_path = next((p for p in MODEL_CANDIDATES if p.is_file()), None)
    if ckpt_path is None:
        _error = "upperwear6/upperwear3 checkpoint not found"
        return
    try:
        _torch = torch
        ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
        _labels = list(ckpt.get("classes") or ["shirt", "t-shirt", "jacket"])
        model = models.resnet18(weights=None)
        model.fc = torch.nn.Linear(model.fc.in_features, len(_labels))
        model.load_state_dict(ckpt["model_state"])
        model.eval()
        _model = model
        _transform = transforms.Compose(
            [
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225)),
            ]
        )
        _error = ""
    except Exception as exc:  # noqa: BLE001
        _model = None
        _error = str(exc)


def classify_garment(image: Image.Image) -> dict[str, Any] | None:
    """Return an upperwear or dress label — never pants/shorts/skirt."""
    _ensure_loaded()
    if _model is None or _torch is None or _transform is None:
        return None
    batch = _transform(image.convert("RGB")).unsqueeze(0)
    with _torch.no_grad():
        probs = _torch.softmax(_model(batch), dim=1)[0]
    ranked_all = sorted(
        ((_labels[i], float(probs[i])) for i in range(len(_labels))),
        key=lambda row: row[1],
        reverse=True,
    )
    ranked = [(n, s) for n, s in ranked_all if n in UPPERWEAR_LABELS]
    if not ranked:
        return None
    label, confidence = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0.0
    # Keep the 6-class argmax. Marking shirt/t-shirt/jacket "unknown" on a
    # close race lets binary gates steal hoodies, tops, and gowns.
    uncertain = confidence < 0.32
    category = CLASS_TO_CATEGORY.get(label, "upperwear")
    if label == "dress":
        category = "dress"
    return {
        "category": "accessories" if uncertain else category,
        "subcategory": label if not uncertain else "unknown",
        "confidence": float(confidence),
        "usedFallback": uncertain,
        "source": "upperwear",
        "message": (
            "Uncertain upperwear. Please select the type."
            if uncertain
            else f"Detected {DISPLAY_NAME.get(label, label)} ({confidence * 100:.0f}%)."
        ),
        "displayName": "Unknown/Uncertain" if uncertain else DISPLAY_NAME.get(label, label),
        "items": [],
        "ranked": [
            {"subcategory": n, "displayName": DISPLAY_NAME.get(n, n), "confidence": s}
            for n, s in ranked
        ],
    }
