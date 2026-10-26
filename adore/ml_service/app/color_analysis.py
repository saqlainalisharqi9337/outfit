"""Per-garment multi-color analysis (independent of clothing class).

Pipeline
  crop the detector box
  -> isolate garment pixels (GrabCut, else Lab border flood)
  -> gray-world white-balance on those pixels only
  -> K-Means in CIE Lab (area, not brightness)
  -> name clusters from a fixed palette
  -> drop tiny clusters (logos / buttons)
  -> primary / secondary / accent by share
  -> pattern from the spatial cluster map

Open-source methods: CIE Lab (CIE 1976), gray-world constancy,
OpenCV GrabCut (Rother et al., 2004), K-Means. No garment class is
read here — type comes from the existing detector/classifiers.
"""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass, field
from typing import Any, Iterable

import numpy as np
from PIL import Image, ImageDraw

from .config import get_settings

# Controlled vocabulary requested by the product. Flutter catalog names are
# a subset; CATALOG_NAME maps extras onto existing recommendation colours.
PALETTE_RGB: dict[str, tuple[int, int, int]] = {
    "black": (22, 22, 22),
    "white": (246, 246, 246),
    "gray": (128, 128, 128),
    "red": (196, 32, 40),
    "dark_red": (118, 18, 24),
    "orange": (230, 122, 32),
    "yellow": (232, 198, 48),
    "green": (36, 132, 68),
    "dark_green": (22, 72, 40),
    "blue": (40, 82, 178),
    "navy": (18, 32, 78),
    "light_blue": (118, 178, 218),
    "purple": (118, 58, 148),
    "pink": (220, 118, 148),
    "brown": (110, 70, 40),
    "beige": (210, 190, 154),
    "cream": (245, 236, 214),
    "maroon": (112, 22, 42),
    "gold": (198, 158, 48),
    "silver": (178, 178, 184),
}

CATALOG_NAME: dict[str, str] = {
    "gray": "grey",
    "dark_red": "maroon",
    "dark_green": "olive",
    "light_blue": "blue",
    "silver": "grey",
}

_PALETTE_LAB: dict[str, np.ndarray] | None = None


@dataclass
class ColorCluster:
    name: str
    catalog_name: str
    share: float
    rgb: tuple[int, int, int]
    hsv: tuple[float, float, float]
    lab: tuple[float, float, float]
    pixel_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "catalogName": self.catalog_name,
            "share": round(float(self.share), 4),
            "percent": round(float(self.share) * 100, 1),
            "rgb": list(self.rgb),
            "hsv": [round(v, 3) for v in self.hsv],
            "lab": [round(v, 2) for v in self.lab],
            "pixelCount": int(self.pixel_count),
        }


@dataclass
class ColorAnalysis:
    primary_color: str
    secondary_colors: list[str]
    accent_colors: list[str]
    color_distribution: dict[str, float]
    pattern: str
    is_multicolor: bool
    clusters: list[ColorCluster] = field(default_factory=list)
    catalog_primary: str = "black"
    catalog_secondary: str | None = None
    pattern_confidence: float = 0.0
    debug: dict[str, Any] = field(default_factory=dict)

    @property
    def pattern_type(self) -> str:
        if self.pattern == "solid":
            return "solid"
        if self.is_multicolor:
            return "multicolor"
        return "patterned"

    def to_api(self) -> dict[str, Any]:
        dist = {k: round(float(v), 4) for k, v in self.color_distribution.items()}
        return {
            "color": self.catalog_primary,
            "secondaryColor": self.catalog_secondary,
            "primaryColor": self.primary_color,
            "secondaryColors": list(self.secondary_colors),
            "accentColors": list(self.accent_colors),
            "colorDistribution": dist,
            "pattern": self.pattern,
            "patternType": self.pattern_type,
            "isMulticolor": bool(self.is_multicolor),
            "patternConfidence": round(float(self.pattern_confidence), 3),
            "colorClusters": [c.to_dict() for c in self.clusters],
        }


def catalog_color(name: str | None) -> str:
    if not name:
        return "black"
    key = str(name).strip().lower().replace(" ", "_")
    mapped = CATALOG_NAME.get(key, key)
    if mapped == "gray":
        return "grey"
    return mapped


def analyze_garment_colors(
    image: Image.Image,
    bbox: Iterable[float] | None = None,
    mask: np.ndarray | None = None,
    *,
    debug: bool = False,
) -> ColorAnalysis:
    """Extract colours from one garment. ``bbox`` is xyxy in 0–1 image coords."""
    settings = get_settings()
    crop, origin = _crop_box(image.convert("RGB"), bbox, settings.color_inset)
    rgb = _resize_max(np.asarray(crop, dtype=np.uint8), settings.color_max_side)
    if mask is not None:
        fg = _resize_mask(mask, rgb.shape[:2])
    else:
        fg = _foreground_mask(rgb)
    if int(fg.sum()) < 40:
        fg = np.ones(rgb.shape[:2], dtype=bool)
        margin = max(2, int(min(rgb.shape[:2]) * 0.12))
        fg[:margin, :] = False
        fg[-margin:, :] = False
        fg[:, :margin] = False
        fg[:, -margin:] = False

    balanced = _gray_world(rgb, fg)
    lab = rgb_to_lab(balanced)
    pixels = lab[fg]
    rgb_pix = balanced[fg]
    if len(pixels) < 20:
        fallback = _name_lab(lab.reshape(-1, 3).mean(axis=0))
        return _single(fallback, debug=debug)

    labels, centers = _cluster_lab(pixels, k_max=settings.color_k_max)
    groups, merged_labels = _merge_and_name(
        labels,
        centers,
        rgb_pix,
        min_share=settings.color_min_share,
        merge_lab=settings.color_merge_lab,
    )
    if not groups:
        fallback = _name_lab(pixels.mean(axis=0))
        return _single(fallback, debug=debug)

    ranked = sorted(groups, key=lambda g: g["share"], reverse=True)
    primary = ranked[0]
    secondary: list[str] = []
    accent: list[str] = []
    for row in ranked[1:]:
        share = float(row["share"])
        name = str(row["name"])
        if name == primary["name"]:
            continue
        if share >= settings.color_secondary_min and len(secondary) < 3:
            secondary.append(name)
        elif share >= settings.color_accent_min and len(accent) < 2:
            accent.append(name)

    dist = {str(row["name"]): float(row["share"]) for row in ranked}
    clusters = [
        ColorCluster(
            name=str(row["name"]),
            catalog_name=catalog_color(str(row["name"])),
            share=float(row["share"]),
            rgb=tuple(int(v) for v in row["rgb"]),
            hsv=_hsv_tuple(np.array(row["rgb"], dtype=np.float64)),
            lab=tuple(float(v) for v in row["lab"]),
            pixel_count=int(row["count"]),
        )
        for row in ranked
    ]
    label_map = _label_map(fg, merged_labels)
    pattern, p_conf = _pattern_from_map(
        label_map,
        dist,
        primary_name=str(primary["name"]),
        solid_min=settings.color_solid_min,
    )
    is_multi = len(secondary) + len(accent) >= 1 or (
        len(dist) >= 2 and float(primary["share"]) < settings.color_solid_min
    )
    analysis = ColorAnalysis(
        primary_color=str(primary["name"]),
        secondary_colors=secondary,
        accent_colors=accent,
        color_distribution=dist,
        pattern=pattern,
        is_multicolor=is_multi,
        clusters=clusters,
        catalog_primary=catalog_color(str(primary["name"])),
        catalog_secondary=catalog_color(secondary[0]) if secondary else None,
        pattern_confidence=p_conf,
    )
    if analysis.catalog_secondary == analysis.catalog_primary:
        analysis.catalog_secondary = (
            catalog_color(secondary[1]) if len(secondary) > 1 else None
        )
    if debug:
        analysis.debug = {
            "cropSize": list(rgb.shape[:2][::-1]),
            "foregroundShare": round(float(fg.mean()), 4),
            "bboxOrigin": origin,
            "panels": _debug_panels(balanced, fg, label_map, analysis),
        }
    return analysis


def detect_colors(
    image: Image.Image,
    bbox: Iterable[float] | None = None,
    mask: np.ndarray | None = None,
) -> tuple[str, str | None]:
    """Backward-compatible (primary, secondary) for the existing API."""
    result = analyze_garment_colors(image, bbox=bbox, mask=mask)
    return result.catalog_primary, result.catalog_secondary


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """Vectorized sRGB uint8 -> CIE Lab (D65)."""
    s = np.clip(rgb.astype(np.float64) / 255.0, 0.0, 1.0)
    linear = np.where(s <= 0.04045, s / 12.92, ((s + 0.055) / 1.055) ** 2.4)
    r, g, b = linear[..., 0], linear[..., 1], linear[..., 2]
    x = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = 0.0193339 * r + 0.1191920 * g + 0.9503041 * b
    xn, yn, zn = 0.95047, 1.00000, 1.08883
    eps, kappa = 216 / 24389, 24389 / 27

    def f(t: np.ndarray) -> np.ndarray:
        return np.where(t > eps, np.cbrt(t), (kappa * t + 16.0) / 116.0)

    fx, fy, fz = f(x / xn), f(y / yn), f(z / zn)
    lab = np.stack([116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz)], axis=-1)
    return lab


def _palette_lab() -> dict[str, np.ndarray]:
    global _PALETTE_LAB
    if _PALETTE_LAB is None:
        _PALETTE_LAB = {
            name: rgb_to_lab(np.array([[rgb]], dtype=np.uint8))[0, 0]
            for name, rgb in PALETTE_RGB.items()
        }
    return _PALETTE_LAB


def _name_lab(lab: np.ndarray) -> str:
    l_val, a_val, b_val = (float(v) for v in lab)
    chroma = float(np.hypot(a_val, b_val))
    if l_val < 16:
        return "black"
    if l_val > 93 and chroma < 8:
        return "white"
    if chroma < 7:
        if l_val > 88:
            return "cream"
        if l_val > 72:
            return "silver" if l_val > 78 else "gray"
        if l_val < 28:
            return "black"
        return "gray"
    best = "gray"
    best_d = 1e9
    sample = np.array([l_val, a_val, b_val], dtype=np.float64)
    for name, centroid in _palette_lab().items():
        d = float(np.linalg.norm(sample - centroid))
        if d < best_d:
            best_d = d
            best = name
    return best


def _single(name: str, *, debug: bool) -> ColorAnalysis:
    return ColorAnalysis(
        primary_color=name,
        secondary_colors=[],
        accent_colors=[],
        color_distribution={name: 1.0},
        pattern="solid",
        is_multicolor=False,
        clusters=[],
        catalog_primary=catalog_color(name),
        catalog_secondary=None,
        pattern_confidence=1.0,
        debug={"note": "too-few-pixels"} if debug else {},
    )


def _crop_box(
    image: Image.Image,
    bbox: Iterable[float] | None,
    inset: float,
) -> tuple[Image.Image, list[int]]:
    width, height = image.size
    if bbox is None:
        box = [0.0, 0.0, 1.0, 1.0]
    else:
        box = [float(v) for v in bbox]
        if len(box) != 4:
            box = [0.0, 0.0, 1.0, 1.0]
    x1, y1, x2, y2 = box
    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)
    bw, bh = max(1e-6, x2 - x1), max(1e-6, y2 - y1)
    x1 += bw * inset
    x2 -= bw * inset
    y1 += bh * inset
    y2 -= bh * inset
    left = int(max(0.0, min(1.0, x1)) * width)
    top = int(max(0.0, min(1.0, y1)) * height)
    right = int(max(0.0, min(1.0, x2)) * width)
    bottom = int(max(0.0, min(1.0, y2)) * height)
    if right - left < 8 or bottom - top < 8:
        return image, [0, 0, width, height]
    return image.crop((left, top, right, bottom)), [left, top, right, bottom]


def _resize_max(rgb: np.ndarray, max_side: int) -> np.ndarray:
    h, w = rgb.shape[:2]
    scale = max(h, w) / float(max(8, max_side))
    if scale <= 1.0:
        return rgb
    image = Image.fromarray(rgb).resize(
        (max(8, int(w / scale)), max(8, int(h / scale))),
        Image.Resampling.BILINEAR,
    )
    return np.asarray(image, dtype=np.uint8)


def _resize_mask(mask: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    h, w = size
    image = Image.fromarray((mask.astype(np.uint8) * 255)).resize(
        (w, h), Image.Resampling.NEAREST
    )
    return np.asarray(image) > 127


def _foreground_mask(rgb: np.ndarray) -> np.ndarray:
    grab = _grabcut_mask(rgb)
    flood = _border_flood_mask(rgb)
    if grab is not None and float(grab.mean()) >= 0.08:
        fg = grab | flood
    else:
        fg = flood
    h, w = rgb.shape[:2]
    inner = np.zeros((h, w), dtype=bool)
    my, mx = max(2, int(h * 0.14)), max(2, int(w * 0.14))
    inner[my : h - my, mx : w - mx] = True
    return fg | inner


def _grabcut_mask(rgb: np.ndarray) -> np.ndarray | None:
    h, w = rgb.shape[:2]
    if min(h, w) < 48:
        return None
    try:
        import cv2
    except ImportError:
        return None
    inset = max(3, int(min(h, w) * 0.08))
    if w - 2 * inset < 8 or h - 2 * inset < 8:
        return None
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    mask = np.zeros((h, w), np.uint8)
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    rect = (inset, inset, w - 2 * inset, h - 2 * inset)
    try:
        cv2.grabCut(bgr, mask, rect, bgd, fgd, 3, cv2.GC_INIT_WITH_RECT)
    except cv2.error:
        return None
    fg = np.where(
        (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), True, False
    )
    kernel = np.ones((3, 3), np.uint8)
    fg = cv2.morphologyEx(fg.astype(np.uint8), cv2.MORPH_OPEN, kernel)
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, kernel).astype(bool)
    return fg


def _border_flood_mask(rgb: np.ndarray) -> np.ndarray:
    lab = rgb_to_lab(rgb)
    h, w, _ = lab.shape
    border = np.concatenate(
        [
            lab[:4, :, :].reshape(-1, 3),
            lab[-4:, :, :].reshape(-1, 3),
            lab[:, :4, :].reshape(-1, 3),
            lab[:, -4:, :].reshape(-1, 3),
        ]
    )
    bg = border.mean(axis=0)
    dist = np.linalg.norm(lab - bg, axis=2)
    like_bg = dist < 18.0
    flooded = _flood(like_bg)
    yy, xx = np.indices((h, w))
    edge = np.minimum.reduce([yy, xx, h - 1 - yy, w - 1 - xx]) / float(max(1, min(h, w)))
    bg = flooded & (edge < 0.18)
    fg = ~bg
    if int(fg.sum()) < max(40, int(h * w * 0.05)):
        like_bg = dist < 10.0
        flooded = _flood(like_bg)
        bg = flooded & (edge < 0.18)
        fg = ~bg
    if int(fg.sum()) < 40:
        fg = np.ones((h, w), dtype=bool)
        m = max(2, int(min(h, w) * 0.12))
        fg[:m, :] = False
        fg[-m:, :] = False
        fg[:, :m] = False
        fg[:, -m:] = False
    return fg


def _flood(like_bg: np.ndarray) -> np.ndarray:
    from collections import deque

    h, w = like_bg.shape
    flooded = np.zeros((h, w), dtype=bool)
    queue: deque[tuple[int, int]] = deque()

    def seed(y: int, x: int) -> None:
        if y < 0 or x < 0 or y >= h or x >= w:
            return
        if flooded[y, x] or not like_bg[y, x]:
            return
        flooded[y, x] = True
        queue.append((y, x))

    for x in range(w):
        seed(0, x)
        seed(h - 1, x)
    for y in range(h):
        seed(y, 0)
        seed(y, w - 1)
    while queue:
        y, x = queue.popleft()
        seed(y + 1, x)
        seed(y - 1, x)
        seed(y, x + 1)
        seed(y, x - 1)
    return flooded


def _gray_world(rgb: np.ndarray, fg: np.ndarray) -> np.ndarray:
    pix = rgb[fg].astype(np.float64)
    if len(pix) == 0:
        return rgb
    mean = pix.mean(axis=0)
    brightness = float(mean.mean())
    # Strong gray-world on a black garment turns it gray; skip extremes.
    if brightness < 48 or brightness > 210:
        return rgb
    gray = float(mean.mean())
    scale = gray / np.maximum(mean, 1.0)
    scale = np.clip(scale, 0.88, 1.12)
    out = np.clip(rgb.astype(np.float64) * scale, 0, 255).astype(np.uint8)
    return out


def _cluster_lab(pixels: np.ndarray, k_max: int) -> tuple[np.ndarray, np.ndarray]:
    n = len(pixels)
    k = int(max(2, min(k_max, n // 40, 6)))
    try:
        from sklearn.cluster import MiniBatchKMeans

        model = MiniBatchKMeans(
            n_clusters=k,
            random_state=0,
            n_init=4,
            batch_size=min(1024, n),
        )
        labels = model.fit_predict(pixels)
        return labels.astype(np.int32), model.cluster_centers_
    except Exception:
        return _numpy_kmeans(pixels, k)


def _numpy_kmeans(pixels: np.ndarray, k: int, iters: int = 14) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(0)
    centers = pixels[rng.choice(len(pixels), size=k, replace=False)].copy()
    labels = np.zeros(len(pixels), dtype=np.int32)
    for _ in range(iters):
        dist = ((pixels[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        labels = dist.argmin(axis=1).astype(np.int32)
        for i in range(k):
            members = pixels[labels == i]
            if len(members):
                centers[i] = members.mean(axis=0)
    return labels, centers


def _merge_and_name(
    labels: np.ndarray,
    centers: np.ndarray,
    rgb_pix: np.ndarray,
    *,
    min_share: float,
    merge_lab: float,
) -> tuple[list[dict[str, Any]], np.ndarray]:
    n = max(1, len(labels))
    raw: list[dict[str, Any]] = []
    for idx in range(int(centers.shape[0])):
        sel = labels == idx
        count = int(sel.sum())
        if count == 0:
            continue
        share = count / n
        lab = centers[idx]
        rgb = rgb_pix[sel].mean(axis=0)
        raw.append(
            {
                "orig": idx,
                "name": _name_lab(lab),
                "share": share,
                "count": count,
                "lab": lab,
                "rgb": np.clip(rgb, 0, 255),
            }
        )
    merged: list[dict[str, Any]] = []
    orig_to_merged: dict[int, int] = {}
    for row in sorted(raw, key=lambda r: r["share"], reverse=True):
        attached = None
        for i, prev in enumerate(merged):
            same_name = prev["name"] == row["name"]
            close = float(np.linalg.norm(prev["lab"] - row["lab"])) < merge_lab
            if same_name or close:
                total = prev["count"] + row["count"]
                prev["lab"] = (prev["lab"] * prev["count"] + row["lab"] * row["count"]) / total
                prev["rgb"] = (prev["rgb"] * prev["count"] + row["rgb"] * row["count"]) / total
                prev["count"] = total
                prev["share"] = total / n
                prev["name"] = _name_lab(prev["lab"])
                attached = i
                break
        if attached is None:
            merged.append(
                {
                    "name": row["name"],
                    "share": row["share"],
                    "count": row["count"],
                    "lab": row["lab"],
                    "rgb": row["rgb"],
                }
            )
            attached = len(merged) - 1
        orig_to_merged[int(row["orig"])] = attached

    kept = [g for g in merged if float(g["share"]) >= min_share]
    if not kept:
        kept = merged[:1]
    name_rank = {g["name"]: i for i, g in enumerate(sorted(kept, key=lambda r: r["share"], reverse=True))}
    remap = np.full(len(labels), -1, dtype=np.int32)
    for orig, mid in orig_to_merged.items():
        if mid >= len(merged):
            continue
        name = str(merged[mid]["name"])
        if name not in name_rank:
            continue
        remap[labels == orig] = name_rank[name]
    kept.sort(key=lambda r: r["share"], reverse=True)
    return kept, remap


def _label_map(fg: np.ndarray, merged_labels: np.ndarray) -> np.ndarray:
    h, w = fg.shape
    canvas = np.full((h, w), -1, dtype=np.int32)
    ys, xs = np.where(fg)
    if len(ys) != len(merged_labels):
        return canvas
    canvas[ys, xs] = merged_labels
    return canvas


def _pattern_from_map(
    label_map: np.ndarray,
    dist: dict[str, float],
    *,
    primary_name: str,
    solid_min: float,
) -> tuple[str, float]:
    shares = sorted(dist.values(), reverse=True)
    primary_share = float(dist.get(primary_name, shares[0] if shares else 1.0))
    n_sig = sum(1 for v in dist.values() if v >= 0.06)
    if n_sig <= 1 or primary_share >= solid_min:
        return "solid", min(1.0, primary_share)

    valid = label_map >= 0
    if int(valid.sum()) < 80:
        return ("printed" if n_sig >= 3 else "patterned"), 0.45

    rows = label_map
    row_changes = _mean_transitions(rows, axis=1)
    col_changes = _mean_transitions(rows, axis=0)
    stripe = False
    checked = False
    if row_changes > 2.2 * max(1.0, col_changes) and row_changes >= 3.5:
        stripe = True
    if col_changes > 2.2 * max(1.0, row_changes) and col_changes >= 3.5:
        stripe = True
    if row_changes >= 3.5 and col_changes >= 3.5:
        ratio = abs(row_changes - col_changes) / max(row_changes, col_changes)
        if ratio < 0.35:
            checked = True
            stripe = False

    non_primary = (label_map != 0) & valid
    components = _component_count(non_primary)

    if checked:
        return "checked", 0.72
    if stripe:
        return "striped", 0.75
    if components >= 8 and 0.08 <= (1.0 - primary_share) <= 0.50:
        return "floral", 0.7
    if n_sig >= 3:
        return "printed", 0.62
    if n_sig == 2:
        a, b = shares[0], shares[1]
        if abs(a - b) < 0.22:
            return "gradient", 0.4
        return "patterned", 0.5
    return "patterned", 0.4


def _mean_transitions(label_map: np.ndarray, axis: int) -> float:
    if axis == 1:
        lines = label_map
    else:
        lines = label_map.T
    changes = []
    for line in lines:
        valid = line[line >= 0]
        if len(valid) < 4:
            continue
        changes.append(float(np.count_nonzero(valid[1:] != valid[:-1])))
    return float(np.mean(changes)) if changes else 0.0


def _component_count(binary: np.ndarray) -> int:
    try:
        import cv2

        n, _ = cv2.connectedComponents(binary.astype(np.uint8), connectivity=8)
        return max(0, int(n) - 1)
    except Exception:
        # Coarse downsample count of on-blobs.
        small = binary[::4, ::4]
        return int(small.sum() // max(1, small.size // 40))


def _hsv_tuple(rgb: np.ndarray) -> tuple[float, float, float]:
    r, g, b = (rgb / 255.0).tolist()
    mx = max(r, g, b)
    mn = min(r, g, b)
    d = mx - mn
    v = mx
    s = 0.0 if mx == 0 else d / mx
    h = 0.0
    if d > 0:
        if mx == r:
            h = ((g - b) / d) % 6
        elif mx == g:
            h = (b - r) / d + 2
        else:
            h = (r - g) / d + 4
        h *= 60
        if h < 0:
            h += 360
    return (h, s, v)


def _debug_panels(
    rgb: np.ndarray,
    fg: np.ndarray,
    label_map: np.ndarray,
    analysis: ColorAnalysis,
) -> dict[str, str]:
    crop = Image.fromarray(rgb)
    mask = Image.fromarray((fg.astype(np.uint8) * 255))
    clustered = _paint_clusters(rgb, label_map, analysis)
    bars = _paint_bars(analysis, width=max(160, rgb.shape[1]))
    return {
        "crop": _png_b64(crop),
        "mask": _png_b64(mask.convert("RGB")),
        "clusters": _png_b64(clustered),
        "distribution": _png_b64(bars),
    }


def _paint_clusters(
    rgb: np.ndarray, label_map: np.ndarray, analysis: ColorAnalysis
) -> Image.Image:
    palette = [c.rgb for c in analysis.clusters] or [(128, 128, 128)]
    out = np.zeros_like(rgb)
    out[label_map < 0] = (30, 30, 30)
    for idx, color in enumerate(palette):
        out[label_map == idx] = color
    leftover = (label_map >= len(palette))
    if leftover.any() and palette:
        out[leftover] = palette[-1]
    return Image.fromarray(out)


def _paint_bars(analysis: ColorAnalysis, width: int) -> Image.Image:
    height = 28 * max(1, len(analysis.clusters)) + 12
    image = Image.new("RGB", (width, height), (18, 18, 18))
    draw = ImageDraw.Draw(image)
    y = 6
    for cluster in analysis.clusters:
        bar_w = max(4, int((width - 12) * cluster.share))
        draw.rectangle([6, y, 6 + bar_w, y + 18], fill=cluster.rgb)
        draw.text((10, y + 2), f"{cluster.name} {cluster.share * 100:.0f}%", fill=(240, 240, 240))
        y += 26
    return image


def _png_b64(image: Image.Image) -> str:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def render_debug_collage(image: Image.Image, analysis: ColorAnalysis) -> Image.Image:
    """Original → crop/mask → clusters → percentages, for visual QA."""
    panels = analysis.debug.get("panels") or {}
    if not panels:
        analysis = analyze_garment_colors(image, debug=True)
        panels = analysis.debug.get("panels") or {}
    parts = []
    for key in ("crop", "mask", "clusters", "distribution"):
        raw = panels.get(key)
        if not raw:
            continue
        parts.append(Image.open(io.BytesIO(base64.b64decode(raw))).convert("RGB"))
    if not parts:
        return image.convert("RGB")
    height = max(p.height for p in parts)
    scaled = []
    for part in parts:
        if part.height != height:
            w = max(8, int(part.width * height / part.height))
            part = part.resize((w, height), Image.Resampling.NEAREST)
        scaled.append(part)
    width = sum(p.width for p in scaled) + 8 * (len(scaled) + 1)
    canvas = Image.new("RGB", (width, height + 16), (12, 12, 12))
    x = 8
    for part in scaled:
        canvas.paste(part, (x, 8))
        x += part.width + 8
    return canvas
