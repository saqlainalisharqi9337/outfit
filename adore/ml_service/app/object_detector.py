"""Detection for outfit photos.

Two optional local weight files, never downloaded at request time:

  * COCO YOLOv8n — ``person`` box plus backpack/handbag (no hat/glasses).
  * Fashionpedia YOLOv8n — bag, hat, glasses, belt, scarf, … (Jia et al.).

DeepFashion2 is not used here: it has no accessory classes, which is why a
bag was labelled skirt and a cap was labelled dress.

Garment labels still come from the MobileNet specialists. This module only
proposes boxes. Missing weights degrade to region proposals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from PIL import Image

from .config import get_settings
from .detection_schema import Bbox, Proposal, normalize_bbox
from .fashionpedia_map import (
    ACCESSORY_FROM_FASHIONPEDIA,
    FASHIONPEDIA_NAMES,
    allowed_leaves,
    hint_leaf,
    name_for_index,
)

# COCO name -> wardrobe leaf the crop is allowed to become.
COCO_TO_ALLOWED: dict[str, frozenset[str]] = {
    "backpack": frozenset({"bag"}),
    "handbag": frozenset({"bag"}),
    "suitcase": frozenset({"bag"}),
}

PERSON_CLASS = "person"

_loaded = False
_model = None
_fashion = None
_pose_loaded = False
_pose_model = None
_error = ""
_fashion_error = ""
_pose_error = ""
_backend = "none"
_model_name = ""
_fashion_name = ""
_pose_name = ""


@dataclass
class DetectorResult:
    """Everything one detector pass produced."""

    available: bool = False
    strategy: str = "none"
    person: Bbox | None = None
    keypoints: list[tuple[float, float, float]] | None = None
    objects: list[Proposal] = field(default_factory=list)
    person_confidence: float = 0.0


def status() -> dict[str, Any]:
    """Health payload. Reports weight *names*, never filesystem paths."""
    _ensure_loaded()
    settings = get_settings()
    payload: dict[str, Any] = {
        "available": _model is not None or _fashion is not None,
        "backend": _backend,
        "model": _model_name,
        "fashionModel": _fashion_name,
        "enabled": settings.detector_enabled,
        "confidence": settings.detector_confidence,
        "cocoClasses": sorted(COCO_TO_ALLOWED) + [PERSON_CLASS],
        "fashionAccessoryClasses": sorted(ACCESSORY_FROM_FASHIONPEDIA),
        "clothingClassesTrained": sorted(ACCESSORY_FROM_FASHIONPEDIA)
        if _fashion is not None
        else [],
        "note": (
            "COCO person detector plus Fashionpedia accessory boxes "
            "(bag, hat, glasses, belt, scarf). Garment type still comes "
            "from the MobileNet classifiers."
        ),
    }
    if _error:
        payload["error"] = _error
    if _fashion_error:
        payload["fashionError"] = _fashion_error
    if settings.pose_weights:
        _ensure_pose_loaded()
        payload["pose"] = {
            "available": _pose_model is not None,
            "model": _pose_name,
            **({"error": _pose_error} if _pose_error else {}),
        }
    return payload


def analyze(image: Image.Image) -> DetectorResult:
    """Run the detector once and return person, pose and object proposals."""
    _ensure_loaded()
    if _model is None and _fashion is None:
        return DetectorResult()

    settings = get_settings()
    rgb = image.convert("RGB")
    objects: list[Proposal] = []
    person: Bbox | None = None
    person_score = 0.0
    available = False

    if _model is not None:
        coco = _predict_rows(_model, rgb, settings.detector_confidence, settings.detector_iou)
        available = True
        names = getattr(_model, "names", {}) or {}
        for idx, box, score in coco:
            name = names.get(idx, str(idx))
            if name == PERSON_CLASS:
                if score > person_score:
                    person, person_score = box, score
                continue
            allowed = COCO_TO_ALLOWED.get(name)
            if allowed is None:
                continue
            if (box[2] - box[0]) < settings.detector_min_box:
                continue
            if (box[3] - box[1]) < settings.detector_min_box:
                continue
            objects.append(
                Proposal(
                    bbox=box,
                    source="yolo",
                    region=f"detect_{name}",
                    allowed=allowed,
                    confidence=score,
                    detector_label=name,
                )
            )

    if _fashion is not None:
        fashion_rows = _predict_rows(
            _fashion, rgb, settings.detector_confidence, settings.detector_iou
        )
        available = True
        names = getattr(_fashion, "names", {}) or {}
        for idx, box, score in fashion_rows:
            if (box[2] - box[0]) < settings.detector_min_box:
                continue
            if (box[3] - box[1]) < settings.detector_min_box:
                continue
            category = name_for_index(idx, names)
            allowed = allowed_leaves(category)
            if allowed is None:
                continue
            objects.append(
                Proposal(
                    bbox=box,
                    source="fashionpedia",
                    region=f"fashion_{category.split(',')[0].replace(' ', '_')}",
                    allowed=allowed,
                    confidence=score,
                    detector_label=category,
                )
            )

    objects.sort(key=lambda p: -p.confidence)
    del objects[settings.detector_max_boxes :]

    keypoints = _keypoints_for(rgb, person) if person is not None else None
    return DetectorResult(
        available=available,
        strategy="detector",
        person=person,
        keypoints=keypoints,
        objects=objects,
        person_confidence=person_score,
    )


def fashionpedia_item_hint(image: Image.Image) -> dict[str, float]:
    """Best Fashionpedia class scores for a single wardrobe photo.

    Uses the already-loaded open-source Fashionpedia YOLOv8n weights.
    Does not change accessory box filtering used by outfit_parser.
    """
    _ensure_loaded()
    if _fashion is None:
        return {}
    settings = get_settings()
    rgb = image.convert("RGB")
    conf = min(float(settings.detector_confidence or 0.35), 0.12)
    rows = _predict_rows(_fashion, rgb, conf, settings.detector_iou)
    names = getattr(_fashion, "names", {}) or {}
    scores: dict[str, float] = {}
    for idx, _box, score in rows:
        leaf = hint_leaf(name_for_index(idx, names))
        if leaf is None:
            continue
        prev = scores.get(leaf, 0.0)
        if score > prev:
            scores[leaf] = float(score)
    return scores


def detect_objects(image: Image.Image) -> list[dict[str, Any]]:
    """Backwards-compatible view of :func:`analyze` used by outfit_parser."""
    result = analyze(image)
    return [
        {
            "bbox": list(p.bbox),
            "allowed": p.allowed,
            "coco": p.detector_label,
            "confidence": p.confidence,
            "region": p.region,
        }
        for p in result.objects
    ]


def _keypoints_for(
    image: Image.Image, person: Bbox
) -> list[tuple[float, float, float]] | None:
    """COCO-17 keypoints in normalized image coordinates, or None."""
    _ensure_pose_loaded()
    if _pose_model is None:
        return None
    settings = get_settings()
    try:
        results = _pose_model.predict(
            image, verbose=False, conf=settings.detector_confidence
        )
    except Exception:  # noqa: BLE001
        return None
    for row in results:
        kp = getattr(row, "keypoints", None)
        xyn = getattr(kp, "xyn", None)
        if xyn is None:
            continue
        data = xyn.tolist()
        scores = getattr(kp, "conf", None)
        score_rows = scores.tolist() if scores is not None else None
        for person_idx, points in enumerate(data):
            if not points:
                continue
            row_scores = (
                score_rows[person_idx]
                if score_rows is not None and person_idx < len(score_rows)
                else [1.0] * len(points)
            )
            return [
                (float(pt[0]), float(pt[1]), float(row_scores[j]))
                for j, pt in enumerate(points)
                if len(pt) >= 2
            ]
    return None


def _predict_rows(model, rgb: Image.Image, conf: float, iou: float) -> list[tuple[int, Bbox, float]]:
    try:
        results = model.predict(rgb, verbose=False, conf=conf, iou=iou)
    except Exception:  # noqa: BLE001
        return []
    rows: list[tuple[int, Bbox, float]] = []
    for row in results or []:
        boxes = getattr(row, "boxes", None)
        xyxyn = getattr(boxes, "xyxyn", None)
        if xyxyn is None:
            continue
        cls = getattr(boxes, "cls", None)
        scores = getattr(boxes, "conf", None)
        for i, raw in enumerate(xyxyn.tolist()):
            box = normalize_bbox(raw[:4])
            if box is None:
                continue
            idx = int(cls[i].item()) if cls is not None else -1
            score = float(scores[i].item()) if scores is not None else 0.0
            rows.append((idx, box, score))
    return rows


def _ensure_loaded() -> None:
    global _loaded, _model, _fashion, _error, _fashion_error, _backend, _model_name
    global _fashion_name
    if _loaded:
        return
    _loaded = True
    settings = get_settings()
    if not settings.detector_enabled:
        _error = "Detector disabled by ADORE_DETECTOR_ENABLED."
        return
    try:
        from ultralytics import YOLO
    except Exception as exc:  # noqa: BLE001
        _error = str(exc)
        return

    weight = settings.resolve_weights(settings.detector_weights)
    if weight is None:
        _error = (
            f"No detector weights named '{settings.detector_weights}' in models/. "
            "Using region proposals for the person box."
        )
    else:
        try:
            _model = YOLO(str(weight))
            _backend = "ultralytics"
            _model_name = weight.name
        except Exception as exc:  # noqa: BLE001
            _error = str(exc)
            _model = None

    fashion_weight = settings.resolve_weights(settings.fashion_weights)
    if fashion_weight is None:
        _fashion_error = (
            f"No Fashionpedia weights named '{settings.fashion_weights}' in models/."
        )
    else:
        try:
            _fashion = YOLO(str(fashion_weight), task="detect")
            try:
                names = getattr(_fashion, "names", None) or {}
                sample = str(next(iter(names.values()), ""))
                if not names or sample.isdigit():
                    mapped = {i: name for i, name in enumerate(FASHIONPEDIA_NAMES)}
                    _fashion.names = mapped
            except Exception:  # noqa: BLE001
                pass
            _fashion_name = fashion_weight.name
            _backend = "ultralytics"
        except Exception as exc:  # noqa: BLE001
            _fashion_error = str(exc)
            _fashion = None


def _ensure_pose_loaded() -> None:
    global _pose_loaded, _pose_model, _pose_error, _pose_name
    if _pose_loaded:
        return
    _pose_loaded = True
    settings = get_settings()
    if not settings.pose_weights:
        return
    weight = settings.resolve_weights(settings.pose_weights)
    if weight is None:
        _pose_error = f"No pose weights named '{settings.pose_weights}' in models/."
        return
    try:
        from ultralytics import YOLO

        _pose_model = YOLO(str(weight))
        _pose_name = weight.name
    except Exception as exc:  # noqa: BLE001
        _pose_error = str(exc)
        _pose_model = None


def reset() -> None:
    """Force the next call to reload. Used by tests."""
    global _loaded, _model, _fashion, _error, _fashion_error, _backend, _model_name
    global _fashion_name, _pose_loaded, _pose_model, _pose_error, _pose_name
    _loaded = False
    _model = None
    _fashion = None
    _error = ""
    _fashion_error = ""
    _backend = "none"
    _model_name = ""
    _fashion_name = ""
    _pose_loaded = False
    _pose_model = None
    _pose_error = ""
    _pose_name = ""
