"""Environment-driven settings for the Adore ML service.

Every tunable that used to be a module-level constant scattered across
``object_detector`` and ``outfit_parser`` is collected here so the detection
pipeline has one place to look. The defaults are the values those modules
already used, so importing this module changes no behaviour on its own.

Environment variables (all optional):

  ADORE_DETECTOR_ENABLED      "1"/"0"  - master switch, default on
  ADORE_DETECTOR_WEIGHTS      str      - COCO person detector in models/
  ADORE_FASHION_WEIGHTS       str      - Fashionpedia YOLO for accessories
  ADORE_DETECTOR_CONFIDENCE   float    - YOLO score floor for a proposal
  ADORE_DETECTOR_IOU          float    - YOLO NMS IoU
  ADORE_DETECTOR_MIN_BOX      float    - smallest normalized box side kept
  ADORE_DETECTOR_MAX_BOXES    int      - cap on proposals per image
  ADORE_POSE_WEIGHTS          str      - optional pose weights, disabled if unset
  ADORE_CLASSIFIER_MIN_CONF   float    - crop classification floor
  ADORE_REFINE_MIN_CONF       float    - floor for a refined label to replace a proposal
  ADORE_ITEM_MIN_CONF         float    - floor for an item to appear in the response
  ADORE_HUMAN_REVIEW_MIN_CONF float    - below this, predictions need human review
  ADORE_MIN_CROP_PX           int      - smallest crop side in pixels
  ADORE_CORS_ORIGINS          str      - comma-separated origins, or "*" (default)
  ADORE_API_KEY               str      - if set, require matching X-API-Key header
  ADORE_COLOR_MIN_SHARE       float    - drop clusters smaller than this (logos)
  ADORE_COLOR_SECONDARY_MIN   float    - share needed to count as secondary
  ADORE_COLOR_ACCENT_MIN      float    - share needed to count as accent
  ADORE_COLOR_SOLID_MIN       float    - primary share that counts as solid
  ADORE_COLOR_MERGE_LAB       float    - merge clusters closer than this in Lab
  ADORE_COLOR_INSET           float    - crop inset to reduce background leak
  ADORE_COLOR_K_MAX           int      - max K-Means clusters before merge
  ADORE_COLOR_MAX_SIDE        int      - analysis resize (pixels)
  ADORE_COLOR_DEBUG           "1"/"0"  - write debug collages when requested
  ADORE_MASKRCNN_ENABLED      "1"/"0"  - live clothing path is MobileNetV2; set 1 to use Mask R-CNN
  ADORE_MASKRCNN_SCORE        float    - score floor, default 0.50
  ADORE_MASKRCNN_CHECKPOINT   str      - optional path; default is checkpoints/maskrcnn/m4_11
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_str(name: str, default: str) -> str:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip()


@dataclass(frozen=True)
class Settings:
    """Resolved configuration for one process."""

    detector_enabled: bool
    detector_weights: str
    fashion_weights: str
    detector_confidence: float
    detector_iou: float
    detector_min_box: float
    detector_max_boxes: int
    pose_weights: str
    classifier_min_confidence: float
    refine_min_confidence: float
    item_min_confidence: float
    human_review_min_confidence: float
    min_crop_px: int
    cors_origins: tuple[str, ...] = field(default_factory=lambda: ("*",))
    api_key: str = ""
    color_min_share: float = 0.04
    color_secondary_min: float = 0.12
    color_accent_min: float = 0.06
    color_solid_min: float = 0.82
    color_merge_lab: float = 14.0
    color_inset: float = 0.06
    color_k_max: int = 6
    color_max_side: int = 256
    color_debug: bool = False
    maskrcnn_enabled: bool = True
    maskrcnn_score: float = 0.50
    maskrcnn_checkpoint: str = ""

    def resolve_weights(self, name: str) -> Path | None:
        """Absolute path for a weight name, or None when it is not on disk.

        A bare filename is looked up in ``models/``. Ultralytics would happily
        download a missing checkpoint from the internet; returning None instead
        keeps that decision explicit and offline-safe.
        """
        if not name:
            return None
        candidate = Path(name)
        if not candidate.is_absolute():
            candidate = MODELS_DIR / name
        return candidate if candidate.is_file() else None


_cached: Settings | None = None


def _cors_origins() -> tuple[str, ...]:
    raw = _env_str("ADORE_CORS_ORIGINS", "*")
    parts = tuple(p.strip() for p in raw.split(",") if p.strip())
    return parts or ("*",)


def get_settings() -> Settings:
    global _cached
    if _cached is None:
        _cached = Settings(
            detector_enabled=_env_bool("ADORE_DETECTOR_ENABLED", True),
            detector_weights=_env_str("ADORE_DETECTOR_WEIGHTS", "yolov8n.pt"),
            fashion_weights=_env_str(
                "ADORE_FASHION_WEIGHTS",
                "yolov8n-fashionpedia-1.torchscript",
            ),
            # 0.35 / 0.04 are the values object_detector.py already used.
            detector_confidence=_env_float("ADORE_DETECTOR_CONFIDENCE", 0.35),
            detector_iou=_env_float("ADORE_DETECTOR_IOU", 0.70),
            detector_min_box=_env_float("ADORE_DETECTOR_MIN_BOX", 0.04),
            detector_max_boxes=_env_int("ADORE_DETECTOR_MAX_BOXES", 24),
            pose_weights=_env_str("ADORE_POSE_WEIGHTS", ""),
            # 0.38 / 0.12 / 36 are outfit_parser.py's existing MIN_CONF,
            # _as_item floor and MIN_CROP.
            classifier_min_confidence=_env_float("ADORE_CLASSIFIER_MIN_CONF", 0.38),
            refine_min_confidence=_env_float("ADORE_REFINE_MIN_CONF", 0.38),
            item_min_confidence=_env_float("ADORE_ITEM_MIN_CONF", 0.12),
            # Below this confidence (or usedFallback/unknown), route to human review.
            human_review_min_confidence=_env_float("ADORE_HUMAN_REVIEW_MIN_CONF", 0.45),
            min_crop_px=_env_int("ADORE_MIN_CROP_PX", 36),
            cors_origins=_cors_origins(),
            api_key=_env_str("ADORE_API_KEY", ""),
            color_min_share=_env_float("ADORE_COLOR_MIN_SHARE", 0.04),
            color_secondary_min=_env_float("ADORE_COLOR_SECONDARY_MIN", 0.12),
            color_accent_min=_env_float("ADORE_COLOR_ACCENT_MIN", 0.06),
            color_solid_min=_env_float("ADORE_COLOR_SOLID_MIN", 0.82),
            color_merge_lab=_env_float("ADORE_COLOR_MERGE_LAB", 14.0),
            color_inset=_env_float("ADORE_COLOR_INSET", 0.06),
            color_k_max=_env_int("ADORE_COLOR_K_MAX", 6),
            color_max_side=_env_int("ADORE_COLOR_MAX_SIDE", 256),
            color_debug=_env_bool("ADORE_COLOR_DEBUG", False),
            maskrcnn_enabled=_env_bool("ADORE_MASKRCNN_ENABLED", False),
            maskrcnn_score=_env_float("ADORE_MASKRCNN_SCORE", 0.50),
            maskrcnn_checkpoint=_env_str("ADORE_MASKRCNN_CHECKPOINT", ""),
        )
    return _cached


def reset_settings() -> None:
    """Drop the cache so a test can change the environment and re-read it."""
    global _cached
    _cached = None
