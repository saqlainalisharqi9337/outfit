"""Binary gate: dress vs upperwear (shirt/t-shirt/jacket pooled).

Used to stop tops from being locked as one-piece dress by the silhouette head.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_PATH = MODELS_DIR / "dress_upperwear_gate.pt"

MIN_CONFIDENCE = 0.55

_model = None
_labels: list[str] = ["dress", "upperwear"]
_loaded = False
_error = ""
_torch = None
_transform = None


def status() -> dict[str, Any]:
    _ensure_loaded()
    return {"loaded": _model is not None, "classes": list(_labels), "error": _error}


def _ensure_loaded() -> None:
    global _model, _labels, _loaded, _error, _torch, _transform
    if _loaded:
        return
    _loaded = True
    if not MODEL_PATH.is_file():
        _error = "dress_upperwear_gate.pt not found"
        return
    try:
        import torch
        from torchvision import models, transforms

        _torch = torch
        ckpt = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
        _labels = list(ckpt.get("classes") or ["dress", "upperwear"])
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


def classify_dress_vs_upperwear(image: Image.Image) -> dict[str, Any] | None:
    _ensure_loaded()
    if _model is None or _torch is None or _transform is None:
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
    return {
        "label": label,
        "confidence": confidence,
        "ranked": [{"subcategory": n, "confidence": s} for n, s in ranked],
        "preferUpperwear": label == "upperwear" and confidence >= MIN_CONFIDENCE,
        "preferDress": label == "dress" and confidence >= MIN_CONFIDENCE,
    }
