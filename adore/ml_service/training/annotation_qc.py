"""Validate COCO-style boxes and segmentations. Never invent replacements."""

from __future__ import annotations

from typing import Any


def clip_bbox(bbox: list[float], width: int, height: int) -> list[float] | None:
    if len(bbox) != 4:
        return None
    x, y, w, h = (float(v) for v in bbox)
    if w <= 0 or h <= 0:
        return None
    x1 = min(max(x, 0.0), float(width))
    y1 = min(max(y, 0.0), float(height))
    x2 = min(max(x + w, 0.0), float(width))
    y2 = min(max(y + h, 0.0), float(height))
    nw, nh = x2 - x1, y2 - y1
    if nw <= 0 or nh <= 0:
        return None
    return [x1, y1, nw, nh]


def bbox_was_clipped(original: list[float], clipped: list[float], tol: float = 0.5) -> bool:
    return any(abs(a - b) > tol for a, b in zip(original, clipped))


def polygon_ok(segmentation: Any, width: int, height: int) -> bool:
    if segmentation is None:
        return False
    if isinstance(segmentation, dict):
        size = segmentation.get("size")
        counts = segmentation.get("counts")
        if not counts:
            return False
        if isinstance(size, (list, tuple)) and len(size) == 2:
            return int(size[0]) > 0 and int(size[1]) > 0
        return True
    if not isinstance(segmentation, list) or not segmentation:
        return False
    polys = segmentation if isinstance(segmentation[0], (list, tuple)) else [segmentation]
    ok_any = False
    for poly in polys:
        if not isinstance(poly, (list, tuple)) or len(poly) < 6 or len(poly) % 2:
            return False
        xs = [float(poly[i]) for i in range(0, len(poly), 2)]
        ys = [float(poly[i]) for i in range(1, len(poly), 2)]
        if max(xs) < 0 or max(ys) < 0 or min(xs) > width or min(ys) > height:
            return False
        ok_any = True
    return ok_any


def is_tiny(bbox: list[float], min_area: float, min_side: float) -> bool:
    _x, _y, w, h = bbox
    return (w * h) < min_area or w < min_side or h < min_side


def annotation_key(image_id: int, category_id: int, bbox: list[float]) -> tuple:
    return (
        int(image_id),
        int(category_id),
        round(float(bbox[0]), 1),
        round(float(bbox[1]), 1),
        round(float(bbox[2]), 1),
        round(float(bbox[3]), 1),
    )


def average_hash_bytes(rgb_bytes: bytes, width: int, height: int) -> int:
    """64-bit average hash without extra dependencies. rgb_bytes is 8x8 RGB."""
    del width, height
    pixels = list(rgb_bytes)
    if len(pixels) < 8 * 8 * 3:
        return 0
    greys = []
    for i in range(0, 8 * 8 * 3, 3):
        greys.append((pixels[i] + pixels[i + 1] + pixels[i + 2]) / 3.0)
    mean = sum(greys) / len(greys)
    bits = 0
    for i, value in enumerate(greys):
        if value >= mean:
            bits |= 1 << i
    return bits


def hamming64(a: int, b: int) -> int:
    return (a ^ b).bit_count()
