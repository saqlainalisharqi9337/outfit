"""Optional M4.11 Mask R-CNN detector.

The live clothing API does not load this model. Set ADORE_MASKRCNN_ENABLED=1
to use checkpoints/maskrcnn/m4_11/best_model.pth. The checkpoint is never
written and is not required for MobileNetV2 classification.
"""

from __future__ import annotations

import logging
import sys
import threading
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .config import get_settings
from .detection_schema import normalize_bbox

logger = logging.getLogger("adore.ml.maskrcnn")

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHECKPOINT = REPO_ROOT / "checkpoints" / "maskrcnn" / "m4_11" / "best_model.pth"

# Production category strings Flutter already accepts. jumpsuit is a dress
# family. Do not emit the research label "one-piece".
LABELS: dict[str, tuple[str, str]] = {
    "shirt": ("upperwear", "shirt"),
    "jacket": ("upperwear", "jacket"),
    "sweater": ("upperwear", "sweater"),
    "trousers": ("lowerwear", "trousers"),
    "shorts": ("lowerwear", "shorts"),
    "skirt": ("lowerwear", "skirt"),
    "dress": ("dress", "dress"),
    "jumpsuit": ("dress", "jumpsuit"),
    "shoes": ("footwear", "shoes"),
    "bag": ("accessories", "bag"),
    "hat": ("accessories", "hat"),
    "belt": ("accessories", "belt"),
    "scarf": ("accessories", "scarf"),
    "watch": ("accessories", "watch"),
    "sunglasses": ("accessories", "sunglasses"),
}

_lock = threading.Lock()
_model = None
_names: list[str] = []
_loaded = False
_error = ""
_epoch: int | None = None


def checkpoint_path() -> Path:
    raw = get_settings().maskrcnn_checkpoint
    if raw:
        return Path(raw)
    return DEFAULT_CHECKPOINT


def status() -> dict[str, Any]:
    path = checkpoint_path()
    return {
        "enabled": get_settings().maskrcnn_enabled,
        "loaded": _model is not None,
        "checkpoint": str(path),
        "checkpointPresent": path.is_file(),
        "epoch": _epoch,
        "scoreThreshold": get_settings().maskrcnn_score,
        "resolution": "416x624",
        "error": _error,
    }


def detect_items(image: Image.Image) -> list[dict[str, Any]] | None:
    """Return wardrobe items, an empty list, or None when the model cannot run.

    None tells the parser to keep the previous detector. An empty list means
    the model ran and found nothing.
    """
    if not get_settings().maskrcnn_enabled:
        return None
    try:
        model, names = _ensure_loaded()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Mask R-CNN checkpoint unavailable: %s", exc)
        return None
    rgb = image.convert("RGB")
    width, height = rgb.size
    if width < 2 or height < 2:
        return []
    try:
        import torch

        array = np.array(rgb, dtype=np.float32).transpose(2, 0, 1) / 255.0
        tensor = torch.from_numpy(array)
        with _lock:
            with torch.no_grad():
                pred = model([tensor])[0]
        scores = pred["scores"].detach().cpu()
        labels = pred["labels"].detach().cpu()
        boxes = pred["boxes"].detach().cpu()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Mask R-CNN inference failed: %s", exc)
        return None

    floor = get_settings().maskrcnn_score
    items: list[dict[str, Any]] = []
    for i in range(int(scores.shape[0])):
        score = float(scores[i])
        if score < floor:
            continue
        index = int(labels[i]) - 1
        if index < 0 or index >= len(names):
            continue
        name = names[index]
        mapped = LABELS.get(name)
        if mapped is None:
            continue
        raw = boxes[i].tolist()
        box = normalize_bbox(
            [raw[0] / width, raw[1] / height, raw[2] / width, raw[3] / height]
        )
        if box is None:
            continue
        category, subcategory = mapped
        items.append(
            {
                "class": subcategory,
                "category": category,
                "subcategory": subcategory,
                "confidence": score,
                "bbox": box,
                "source": "maskrcnn",
                "region": "maskrcnn",
                "usedFallback": False,
            }
        )
    items.sort(key=lambda row: -float(row["confidence"]))
    return items[: get_settings().detector_max_boxes]


def _ensure_loaded():
    global _model, _names, _loaded, _error, _epoch
    if _loaded and _model is not None:
        return _model, _names
    with _lock:
        if _loaded and _model is not None:
            return _model, _names
        path = checkpoint_path()
        if not path.is_file():
            _loaded = True
            _error = f"checkpoint not found: {path}"
            raise FileNotFoundError(_error)
        import torch

        service_root = REPO_ROOT / "ml_service"
        if str(service_root) not in sys.path:
            sys.path.insert(0, str(service_root))
        from training.train_maskrcnn import apply_cpu_fast, build_maskrcnn, load_checkpoint

        meta = torch.load(path, map_location="cpu", weights_only=False)
        cfg = meta.get("config") or {}
        names = list(meta.get("class_names") or [])
        if len(names) != 15:
            raise RuntimeError(f"expected 15 class names, found {len(names)}")
        model = build_maskrcnn(
            int(meta.get("num_classes") or 16),
            pretrained=False,
            min_size=int(cfg.get("min_size") or 416),
            max_size=int(cfg.get("max_size") or 624),
            smoke_rpn=True,
        )
        load_checkpoint(path, model, map_location="cpu")
        apply_cpu_fast(model)
        model.eval()
        _model = model
        _names = names
        _epoch = int(meta.get("epoch") or 0)
        _loaded = True
        _error = ""
        logger.info(
            "Loaded Mask R-CNN %s epoch=%s min=%s max=%s",
            path,
            _epoch,
            cfg.get("min_size"),
            cfg.get("max_size"),
        )
        return _model, _names


def reset() -> None:
    """Drop the loaded model. Tests use this; the checkpoint file is not touched."""
    global _model, _names, _loaded, _error, _epoch
    with _lock:
        _model = None
        _names = []
        _loaded = False
        _error = ""
        _epoch = None
