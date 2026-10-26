"""Where to look in an image for each garment family.

Three strategies, best first:

  1. pose      - bands placed on real shoulder/hip/knee/ankle keypoints
  2. person    - bands placed as fractions of the detected person box
  3. fallback  - bands as fractions of the whole image (the original behaviour)

Only (3) assumes the subject is centred and full-length, which is why it is
last. It is kept because it is the only strategy that works when no detector
weights are installed, and the service must still function in that state.

Each strategy returns the same triple, ``(region_name, bbox, allowed)``, so
``outfit_parser`` does not care which one produced it. Region names are stable
because the parser's skip rules match on them.
"""

from __future__ import annotations

from .clothing_taxonomy import FOOTWEAR
from .detection_schema import Bbox, normalize_bbox

UPPER_LABELS = frozenset(
    {
        "t-shirt",
        "shirt",
        "hoodie",
        "jacket",
        "coat",
        "sweater",
        "blouse",
        "dress",
        "kurta",
        "kameez",
        "cardigan",
        "blazer",
        "modest top",
    }
)

LOWER_LABELS = frozenset(
    {
        "trousers",
        "jeans",
        "shorts",
        "skirt",
        "palazzo",
        "shalwar",
        "chinos",
        "dress",
    }
)

HEAD_LABELS = frozenset({"hat", "hijab", "sunglasses", "scarf", "dupatta"})
BAG_LABELS = frozenset({"bag"})

# Whole-image fractions. Unchanged from the original outfit_parser.REGIONS so
# that behaviour with no detector installed stays byte-for-byte the same.
FALLBACK_REGIONS: tuple[tuple[str, tuple[float, float, float, float], frozenset[str]], ...] = (
    ("headwear", (0.18, 0.00, 0.82, 0.22), HEAD_LABELS),
    ("upper", (0.12, 0.12, 0.88, 0.52), UPPER_LABELS),
    ("lower", (0.14, 0.40, 0.86, 0.84), LOWER_LABELS),
    ("feet", (0.16, 0.72, 0.84, 1.00), frozenset(FOOTWEAR)),
    ("bag_left", (0.00, 0.26, 0.30, 0.78), BAG_LABELS),
    ("bag_right", (0.70, 0.26, 1.00, 0.78), BAG_LABELS),
    ("bag_front", (0.28, 0.38, 0.72, 0.84), BAG_LABELS),
)

# Fractions *of the person box*, not of the image. A person standing off to one
# side, seated, or filling only part of the frame gets correct bands from these
# because the box moves with them.
PERSON_BANDS: tuple[tuple[str, tuple[float, float, float, float], frozenset[str]], ...] = (
    ("headwear", (0.16, 0.00, 0.84, 0.20), HEAD_LABELS),
    ("upper", (0.06, 0.10, 0.94, 0.54), UPPER_LABELS),
    ("lower", (0.08, 0.42, 0.92, 0.88), LOWER_LABELS),
    ("feet", (0.10, 0.84, 0.90, 1.00), frozenset(FOOTWEAR)),
    ("bag_left", (-0.28, 0.24, 0.16, 0.80), BAG_LABELS),
    ("bag_right", (0.84, 0.24, 1.28, 0.80), BAG_LABELS),
    ("bag_front", (0.22, 0.38, 0.78, 0.86), BAG_LABELS),
)

# COCO keypoint indices used to place bands from a pose model.
KP_NOSE = 0
KP_L_SHOULDER, KP_R_SHOULDER = 5, 6
KP_L_HIP, KP_R_HIP = 11, 12
KP_L_KNEE, KP_R_KNEE = 13, 14
KP_L_ANKLE, KP_R_ANKLE = 15, 16

MIN_KP_SCORE = 0.35


def _project(person: Bbox, frac: tuple[float, float, float, float]) -> Bbox | None:
    """Map a person-relative fraction into normalized image coordinates."""
    px1, py1, px2, py2 = person
    pw = px2 - px1
    ph = py2 - py1
    if pw <= 0 or ph <= 0:
        return None
    return normalize_bbox(
        [
            px1 + frac[0] * pw,
            py1 + frac[1] * ph,
            px1 + frac[2] * pw,
            py1 + frac[3] * ph,
        ]
    )


def from_person_box(
    person: Bbox,
) -> list[tuple[str, tuple[float, float, float, float], frozenset[str]]]:
    """Bands anchored to a detected person."""
    regions = []
    for name, frac, allowed in PERSON_BANDS:
        box = _project(person, frac)
        if box is None:
            continue
        regions.append((name, (box[0], box[1], box[2], box[3]), allowed))
    return regions


def _mean_y(points: list[tuple[float, float, float]], *indices: int) -> float | None:
    values = [
        points[i][1]
        for i in indices
        if i < len(points) and points[i][2] >= MIN_KP_SCORE
    ]
    if not values:
        return None
    return sum(values) / len(values)


def from_keypoints(
    points: list[tuple[float, float, float]],
    person: Bbox,
) -> list[tuple[str, tuple[float, float, float, float], frozenset[str]]] | None:
    """Bands placed on real anatomy.

    ``points`` is COCO-17 ``(x, y, score)`` in normalized image coordinates.
    Returns None when the pose is too incomplete to trust, so the caller can
    fall back to the person box.
    """
    shoulder = _mean_y(points, KP_L_SHOULDER, KP_R_SHOULDER)
    hip = _mean_y(points, KP_L_HIP, KP_R_HIP)
    if shoulder is None or hip is None or hip <= shoulder:
        return None

    knee = _mean_y(points, KP_L_KNEE, KP_R_KNEE)
    ankle = _mean_y(points, KP_L_ANKLE, KP_R_ANKLE)
    nose = _mean_y(points, KP_NOSE)

    x1, _, x2, y2 = person
    width = max(x2 - x1, 1e-6)
    torso = max(hip - shoulder, 1e-6)

    head_top = max(0.0, (nose if nose is not None else shoulder) - torso * 0.75)
    hem = ankle if ankle is not None else (knee if knee is not None else y2)
    foot_top = max(hem - torso * 0.25, hip)

    bands: list[tuple[str, tuple[float, float, float, float], frozenset[str]]] = []

    def add(name, box, allowed):
        clean = normalize_bbox(list(box))
        if clean is not None:
            bands.append((name, (clean[0], clean[1], clean[2], clean[3]), allowed))

    add(
        "headwear",
        [x1 + width * 0.20, head_top, x2 - width * 0.20, shoulder],
        HEAD_LABELS,
    )
    add(
        "upper",
        [x1 + width * 0.02, shoulder - torso * 0.12, x2 - width * 0.02, hip + torso * 0.12],
        UPPER_LABELS,
    )
    add(
        "lower",
        [x1 + width * 0.04, hip - torso * 0.10, x2 - width * 0.04, min(hem + torso * 0.10, 1.0)],
        LOWER_LABELS,
    )
    add("feet", [x1, foot_top, x2, min(hem + torso * 0.30, 1.0)], frozenset(FOOTWEAR))
    add("bag_left", [x1 - width * 0.30, shoulder, x1 + width * 0.18, hip + torso * 0.6], BAG_LABELS)
    add("bag_right", [x2 - width * 0.18, shoulder, x2 + width * 0.30, hip + torso * 0.6], BAG_LABELS)
    add("bag_front", [x1 + width * 0.20, shoulder + torso * 0.3, x2 - width * 0.20, hip + torso * 0.8], BAG_LABELS)
    return bands or None


def body_regions(
    person: Bbox | None = None,
    keypoints: list[tuple[float, float, float]] | None = None,
) -> tuple[str, list[tuple[str, tuple[float, float, float, float], frozenset[str]]]]:
    """Pick the best available strategy.

    Returns ``(strategy_name, regions)`` so the caller can report honestly which
    one was used rather than implying detection happened when it did not.
    """
    if person is not None and keypoints:
        bands = from_keypoints(keypoints, person)
        if bands:
            return "pose", bands
    if person is not None:
        bands = from_person_box(person)
        if bands:
            return "person", bands
    return "fallback", list(FALLBACK_REGIONS)
