"""20-class multi-item outfit detector.

Uses the existing Fashionpedia YOLOv8n when the improved 20-class checkpoint
is not present. Never overwrites models/original/.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

from .config import MODELS_DIR, get_settings
from .fashionpedia_map import name_for_index, outfit20_id
from .outfit20_taxonomy import (
    OUTFIT20_CLASSES,
    PARENT,
    SUBCATEGORY,
    class_id,
)

IMPROVED_PATH = MODELS_DIR / "improved" / "outfit20_yolov8n.pt"
ORIGINAL_DIR = MODELS_DIR / "original"

_improved = None
_improved_loaded = False
_improved_error = ""


def status() -> dict[str, Any]:
    _ensure_improved()
    return {
        "classes": list(OUTFIT20_CLASSES),
        "improvedLoaded": _improved is not None,
        "improvedPath": IMPROVED_PATH.name if IMPROVED_PATH.is_file() else "",
        "error": _improved_error,
        "framework": "Ultralytics YOLOv8",
        "originalBackup": str(ORIGINAL_DIR / "yolov8n-fashionpedia-1.torchscript"),
    }


def detect_items(image: Image.Image) -> list[dict[str, Any]]:
    """Return every visible wardrobe item as its own detection."""
    _ensure_improved()
    rgb = image.convert("RGB")
    if _improved is not None:
        return _predict_improved(rgb)
    return _predict_fashionpedia(rgb)


def _predict_improved(rgb: Image.Image) -> list[dict[str, Any]]:
    settings = get_settings()
    try:
        results = _improved.predict(
            rgb, verbose=False, conf=max(0.18, settings.detector_confidence - 0.12)
        )
    except Exception:  # noqa: BLE001
        return []
    items: list[dict[str, Any]] = []
    for row in results or []:
        boxes = getattr(row, "boxes", None)
        if boxes is None:
            continue
        xyxyn = getattr(boxes, "xyxyn", None)
        cls = getattr(boxes, "cls", None)
        scores = getattr(boxes, "conf", None)
        if xyxyn is None:
            continue
        for i, raw in enumerate(xyxyn.tolist()):
            idx = int(cls[i].item()) if cls is not None else -1
            if idx < 0 or idx >= len(OUTFIT20_CLASSES):
                continue
            oid = OUTFIT20_CLASSES[idx]
            items.append(
                _as_detection(
                    oid,
                    float(scores[i].item()) if scores is not None else 0.0,
                    [float(v) for v in raw[:4]],
                    source="outfit20",
                )
            )
    items.sort(key=lambda row: -float(row["confidence"]))
    return items[: settings.detector_max_boxes]


def _predict_fashionpedia(rgb: Image.Image) -> list[dict[str, Any]]:
    from . import object_detector

    object_detector._ensure_loaded()
    fashion = getattr(object_detector, "_fashion", None)
    if fashion is None:
        return []
    settings = get_settings()
    rows = object_detector._predict_rows(
        fashion, rgb, max(0.18, settings.detector_confidence - 0.12), settings.detector_iou
    )
    names = getattr(fashion, "names", {}) or {}
    items: list[dict[str, Any]] = []
    for idx, box, score in rows:
        oid = outfit20_id(name_for_index(idx, names))
        if oid is None:
            continue
        if (box[2] - box[0]) < 0.03 or (box[3] - box[1]) < 0.03:
            continue
        items.append(_as_detection(oid, float(score), list(box), source="fashionpedia"))
    items.sort(key=lambda row: -float(row["confidence"]))
    return items[: settings.detector_max_boxes]


def refine_footwear_and_wraps(
    image: Image.Image, items: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Keep specialist gates for flats/sneakers/loafers/dupatta/hijab."""
    from . import dupatta_gate, flats_gate, heels_gate, sneakers_gate, shoes_gate

    out: list[dict[str, Any]] = []
    width, height = image.size
    hanging = False
    try:
        from .clothing_taxonomy import is_hanging_body_garment

        hanging = is_hanging_body_garment(image)
    except Exception:  # noqa: BLE001
        hanging = False
    for item in items:
        box = item.get("bbox") or [0.0, 0.0, 1.0, 1.0]
        crop = image.crop(
            (
                int(box[0] * width),
                int(box[1] * height),
                int(box[2] * width),
                int(box[3] * height),
            )
        )
        if crop.size[0] < 24 or crop.size[1] < 24:
            out.append(item)
            continue
        sub = item.get("subcategory")
        if sub in {"shoes", "flats", "sneakers", "loafers"}:
            flats = flats_gate.lock_or_prefer_flats(crop, hanging=hanging)
            sneakers = sneakers_gate.lock_or_prefer_sneakers(crop, hanging=hanging)
            shoes = shoes_gate.lock_or_prefer_shoes(crop, hanging=hanging)
            heels = heels_gate.lock_or_prefer_heels(crop, hanging=hanging)
            ranked = [
                row
                for row in (flats, sneakers, shoes, heels)
                if row is not None
            ]
            if ranked:
                best = max(ranked, key=lambda row: float(row.get("confidence") or 0))
                leaf = str(best.get("subcategory") or sub)
                if leaf == "heels":
                    leaf = "shoes"
                    oid = "footwear_shoes"
                else:
                    oid = f"footwear_{leaf.replace('-', '_')}"
                    if oid not in PARENT:
                        oid = "footwear_shoes"
                        leaf = "shoes"
                item = dict(item)
                item["class"] = oid
                item["subcategory"] = leaf
                item["category"] = "footwear"
                item["confidence"] = max(
                    float(item["confidence"]), float(best.get("confidence") or 0)
                )
        if sub == "scarf":
            hit = dupatta_gate.lock_dupatta(crop) or dupatta_gate.prefer_dupatta_over_bag(
                crop
            )
            if hit is not None and float(hit.get("confidence") or 0) >= 0.55:
                item = dict(item)
                item["class"] = "accessories_dupatta"
                item["subcategory"] = "dupatta"
                item["category"] = "accessories"
        out.append(item)
    return out


def _as_detection(
    oid: str, confidence: float, bbox: list[float], *, source: str
) -> dict[str, Any]:
    return {
        "class": oid,
        "category": PARENT[oid],
        "subcategory": SUBCATEGORY[oid],
        "confidence": float(confidence),
        "bbox": bbox,
        "source": source,
        "region": "outfit20",
        "usedFallback": False,
    }


def _ensure_improved() -> None:
    global _improved, _improved_loaded, _improved_error
    if _improved_loaded:
        return
    _improved_loaded = True
    if not IMPROVED_PATH.is_file():
        _improved_error = "improved checkpoint not trained yet; using Fashionpedia YOLO"
        return
    try:
        from ultralytics import YOLO

        _improved = YOLO(str(IMPROVED_PATH))
        _improved_error = ""
    except Exception as exc:  # noqa: BLE001
        _improved = None
        _improved_error = str(exc)
