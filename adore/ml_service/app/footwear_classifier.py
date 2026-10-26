"""Footwear specialist: shoes / flats / sneakers / heels (+ sandals via ImageNet).

Does not train or modify lowerwear or dress models.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

from .clothing_taxonomy import CLASS_TO_CATEGORY, FOOTWEAR

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_CANDIDATES = (
    MODELS_DIR / "footwear4_resnet18.pt",
    MODELS_DIR / "footwear3_resnet18.pt",
)
LABELS_PATH = MODELS_DIR / "footwear4_labels.json"

CLASS_ORDER = ("shoes", "flats", "sneakers", "heels")
DISPLAY_NAME = {
    "shoes": "Shoes",
    "flats": "Flats",
    "sneakers": "Sneakers",
    "heels": "Heels",
    "sandals": "Sandals",
    "boots": "Boots",
    "loafers": "Loafers",
}
# Labels the ResNet head can refine. Never destroy ImageNet-only types.
REFINE_LABELS = frozenset({"shoes", "flats", "sneakers", "heels", "unknown"})
# Keep these unless the loaded checkpoint actually has that class.
PRESERVE_WITHOUT_CLASS = frozenset({"heels", "sandals", "boots", "loafers"})

MIN_CONFIDENCE = 0.40
MIN_GAP = 0.05

_model = None
_labels: list[str] = list(CLASS_ORDER)
_loaded = False
_error = ""
_torch = None
_transform = None


def status() -> dict[str, Any]:
    _ensure_loaded()
    return {
        "loaded": _model is not None,
        "classes": list(_labels) + ["sandals(imagenet)"],
        "error": _error,
    }


def should_override(label: str | None) -> bool:
    lab = label or "unknown"
    if lab not in (FOOTWEAR | {"unknown"}):
        return False
    _ensure_loaded()
    if lab in PRESERVE_WITHOUT_CLASS and lab not in _labels:
        # e.g. heels on footwear3 — never overwrite with shoes/flats/sneakers.
        return False
    if lab in {"sandals", "boots", "loafers"}:
        return False
    return lab in REFINE_LABELS or lab in _labels


def _passthrough_hint(hint: str, conf: float) -> dict[str, Any]:
    display = DISPLAY_NAME.get(hint, hint.title())
    return {
        "category": "footwear",
        "subcategory": hint,
        "confidence": conf,
        "usedFallback": conf < 0.22,
        "source": "imagenet",
        "message": f"Detected {display} ({conf * 100:.0f}%).",
        "displayName": display,
        "items": [],
        "ranked": [{"subcategory": hint, "confidence": conf}],
    }


def _ensure_loaded() -> None:
    global _model, _labels, _loaded, _error, _torch, _transform
    if _loaded:
        return
    _loaded = True
    ckpt_path = next((p for p in MODEL_CANDIDATES if p.is_file()), None)
    if ckpt_path is None:
        _error = "footwear4/footwear3 checkpoint not found"
        return
    try:
        import torch
        from torchvision import models, transforms

        _torch = torch
        ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
        _labels = list(ckpt.get("classes") or CLASS_ORDER)
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


def classify_footwear(
    image: Image.Image,
    *,
    imagenet_hint: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Prefer ImageNet sandals/boots; ResNet for shoes/flats/sneakers/heels."""
    hint = (imagenet_hint or {}).get("subcategory")
    conf = float((imagenet_hint or {}).get("confidence") or 0.45)
    _ensure_loaded()
    # Preserve heels/boots/loafers when the checkpoint cannot predict them.
    if hint in PRESERVE_WITHOUT_CLASS and hint not in _labels:
        return _passthrough_hint(hint, conf)

    if _model is None or _torch is None or _transform is None:
        if hint == "sandals":
            return _passthrough_hint("sandals", conf)
        return None
    batch = _transform(image.convert("RGB")).unsqueeze(0)
    with _torch.no_grad():
        probs = _torch.softmax(_model(batch), dim=1)[0]
    ranked = sorted(
        ((_labels[i], float(probs[i])) for i in range(len(_labels))),
        key=lambda row: row[1],
        reverse=True,
    )
    label, confidence = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0.0
    # ImageNet sandal is often a high heel. Prefer heels from the specialist.
    if hint == "sandals":
        heels_score = next((s for n, s in ranked if n == "heels"), 0.0)
        if heels_score >= 0.28:
            label, confidence = "heels", heels_score
            second = max((s for n, s in ranked if n != "heels"), default=0.0)
        elif confidence < MIN_CONFIDENCE:
            return _passthrough_hint("sandals", conf)
    uncertain = confidence < MIN_CONFIDENCE or (confidence - second) < MIN_GAP
    if hint == "sandals" and uncertain:
        heels_score = next((s for n, s in ranked if n == "heels"), 0.0)
        if heels_score >= 0.25:
            return {
                "category": "footwear",
                "subcategory": "heels",
                "confidence": float(heels_score),
                "usedFallback": False,
                "source": "footwear",
                "message": f"Detected Heels ({heels_score * 100:.0f}%).",
                "displayName": "Heels",
                "items": [],
                "ranked": [
                    {
                        "subcategory": n,
                        "displayName": DISPLAY_NAME.get(n, n),
                        "confidence": s,
                    }
                    for n, s in ranked
                ],
            }
        return _passthrough_hint("sandals", conf)
    return {
        "category": "accessories" if uncertain else CLASS_TO_CATEGORY.get(label, "footwear"),
        "subcategory": "unknown" if uncertain else label,
        "confidence": float(confidence),
        "usedFallback": uncertain,
        "source": "footwear",
        "message": (
            "Uncertain footwear type. Please select shoes, flats, sneakers, or heels."
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
