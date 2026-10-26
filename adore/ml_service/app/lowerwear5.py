"""5-class lowerwear specialist: trousers / shorts / skirt / shalwar / leggings.

Loads ``lowerwear5_resnet18.pt`` when present. Never overwrites the older
3-class trousers/shorts/skirt MobileNet or trousers_gate keras files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

from .clothing_taxonomy import CLASS_TO_CATEGORY

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_PATH = MODELS_DIR / "lowerwear5_resnet18.pt"

LOWERWEAR_LABELS = frozenset(
    {"trousers", "shorts", "skirt", "shalwar", "leggings", "jeans", "palazzo"}
)
DISPLAY_NAME = {
    "trousers": "Trousers/Pants",
    "shorts": "Shorts",
    "skirt": "Skirt",
    "shalwar": "Shalwar",
    "leggings": "Leggings",
    "jeans": "Jeans",
    "palazzo": "Palazzo",
}
CONFUSED_LABELS = {
    "trousers",
    "pants",
    "jeans",
    "shorts",
    "skirt",
    "miniskirt",
    "shalwar",
    "leggings",
    "palazzo",
    "chinos",
    "unknown",
}

MIN_CONFIDENCE = 0.36
MIN_GAP = 0.05

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
    if not MODEL_PATH.is_file():
        _error = "lowerwear5_resnet18.pt not found"
        return
    try:
        _torch = torch
        ckpt = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
        _labels = list(ckpt.get("classes") or list(LOWERWEAR_LABELS))
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


def classify_lowerwear5(image: Image.Image) -> dict[str, Any] | None:
    """Return a lowerwear label — never shirt/dress/shoes."""
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
    ranked = [(n, s) for n, s in ranked_all if n in LOWERWEAR_LABELS]
    if not ranked:
        return None
    label, confidence = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0.0
    uncertain = confidence < MIN_CONFIDENCE or (confidence - second) < MIN_GAP
    if label in {"shorts", "skirt", "shalwar", "leggings"} and confidence >= 0.40:
        uncertain = False
    return {
        "category": "accessories" if uncertain else CLASS_TO_CATEGORY.get(label, "lowerwear"),
        "subcategory": "unknown" if uncertain else label,
        "confidence": float(confidence),
        "usedFallback": uncertain,
        "source": "lowerwear5",
        "message": (
            "Uncertain lowerwear. Please select the type."
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
