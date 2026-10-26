"""Compatibility wrapper around the Lab / K-Means garment colour pipeline.

Older modules imported ``detect_colors`` from this file. Colour is now
computed in ``color_analysis`` from a detector box or crop, not from a
whole-image brightness majority.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np
from PIL import Image

from .color_analysis import analyze_garment_colors, detect_colors as _detect

__all__ = ["detect_colors", "analyze_garment_colors"]


def detect_colors(
    image: Image.Image,
    bbox: Iterable[float] | None = None,
    mask: np.ndarray | None = None,
) -> tuple[str, str | None]:
    return _detect(image, bbox=bbox, mask=mask)
