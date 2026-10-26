"""Internal structures shared by the detector, region proposer and parser.

Two types travel through the pipeline:

  Proposal   - a candidate box before anything has classified it
  Detection  - a classified item, ready to be serialised for Flutter

``Detection.to_item()`` deliberately emits the key names the Flutter client
already parses (``subcategory``, ``secondaryColor``, ``usedFallback`` ...), so
adding the detector does not change the ``/analyze-clothing`` contract.
Refinement fields are additive and optional.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

Bbox = list[float]


def normalize_bbox(raw: Any) -> Bbox | None:
    """Clamp a 4-number box to [0, 1] and reject degenerate or malformed input.

    Returns None rather than raising: a bad box from a detector should drop the
    proposal, not fail the whole request.
    """
    if not isinstance(raw, (list, tuple)) or len(raw) != 4:
        return None
    try:
        x1, y1, x2, y2 = (float(v) for v in raw)
    except (TypeError, ValueError):
        return None
    if any(v != v for v in (x1, y1, x2, y2)):  # NaN
        return None
    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)
    x1 = min(max(x1, 0.0), 1.0)
    y1 = min(max(y1, 0.0), 1.0)
    x2 = min(max(x2, 0.0), 1.0)
    y2 = min(max(y2, 0.0), 1.0)
    if x2 - x1 <= 0.0 or y2 - y1 <= 0.0:
        return None
    return [x1, y1, x2, y2]


def bbox_area(box: Bbox) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


@dataclass(frozen=True)
class Proposal:
    """A candidate region, from a detector or from the region fallback."""

    bbox: Bbox
    source: str
    region: str
    # Labels this region is allowed to produce. Empty means "no restriction".
    allowed: frozenset[str] = frozenset()
    confidence: float = 0.0
    detector_label: str = ""

    @property
    def restricted(self) -> bool:
        return bool(self.allowed)


@dataclass
class Detection:
    """A classified wardrobe item with its geometry and provenance."""

    label: str
    confidence: float
    category: str
    source: str
    bbox: Bbox | None = None
    region: str = ""
    color: str | None = None
    secondary_color: str | None = None
    used_fallback: bool = False
    detector_label: str = ""
    detector_confidence: float = 0.0
    refined_label: str = ""
    refined_confidence: float = 0.0
    extras: dict[str, Any] = field(default_factory=dict)

    def to_item(self) -> dict[str, Any]:
        """Wire shape consumed by DetectedClothingItem on the Flutter side."""
        item: dict[str, Any] = {
            "category": self.category,
            "subcategory": self.label,
            "confidence": round(float(self.confidence), 4),
            "color": self.color,
            "secondaryColor": self.secondary_color,
            "bbox": list(self.bbox) if self.bbox else None,
            "source": self.source,
            "region": self.region,
            "usedFallback": bool(self.used_fallback),
        }
        if self.detector_label:
            item["detectorLabel"] = self.detector_label
            item["detectorConfidence"] = round(float(self.detector_confidence), 4)
        if self.refined_label:
            item["refinedLabel"] = self.refined_label
            item["refinedConfidence"] = round(float(self.refined_confidence), 4)
        if self.extras:
            item.update(self.extras)
        return item


def items_to_dicts(detections: Iterable[Detection]) -> list[dict[str, Any]]:
    return [d.to_item() for d in detections]
