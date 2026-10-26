from __future__ import annotations

import math

import numpy as np
from PIL import Image

# ITA (Individual Typology Angle) is a cosmetic/colorimetric scale, not a medical diagnosis.
# ITA = arctan((L* - 50) / b*) * 180/pi


def _ita_to_label(ita: float) -> str:
    if ita > 55:
        return "veryLight"
    if ita > 41:
        return "light"
    if ita > 28:
        return "medium"
    if ita > 10:
        return "tan"
    if ita > -30:
        return "brown"
    return "deep"


def _rgb_to_lab_approx(rgb: np.ndarray) -> tuple[float, float, float]:
    """sRGB to Lab approximation sufficient for ITA ranking."""
    s = rgb / 255.0
    s = np.where(s > 0.04045, ((s + 0.055) / 1.055) ** 2.4, s / 12.92)
    xyz = s @ np.array(
        [
            [0.4124, 0.3576, 0.1805],
            [0.2126, 0.7152, 0.0722],
            [0.0193, 0.1192, 0.9505],
        ]
    ).T
    xyz = xyz / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), (7.787 * xyz) + 16 / 116)
    l = 116 * f[1] - 16
    a = 500 * (f[0] - f[1])
    b = 200 * (f[1] - f[2])
    return float(l), float(a), float(b)


def analyze_skin_tone(image: Image.Image) -> tuple[str, float | None, bool, str]:
    arr = np.asarray(image.convert("RGB"), dtype=np.uint8)
    h, w, _ = arr.shape
    # Prefer the central face-ish region of a selfie.
    y0, y1 = int(h * 0.18), int(h * 0.62)
    x0, x1 = int(w * 0.28), int(w * 0.72)
    crop = arr[y0:y1, x0:x1]
    pixels = crop.reshape(-1, 3).astype(np.float32)
    r, g, b = pixels[:, 0], pixels[:, 1], pixels[:, 2]
    # Simple skin-like RGB gate; not a biometric model.
    skin = (
        (r > 60)
        & (g > 30)
        & (b > 15)
        & (r > g)
        & (r > b)
        & ((r - g) > 10)
        & ((r - b) > 10)
    )
    selected = pixels[skin]
    used_fallback = False
    if len(selected) < 80:
        selected = pixels
        used_fallback = True
    mean = selected.mean(axis=0)
    l, _a, b_star = _rgb_to_lab_approx(mean)
    if abs(b_star) < 1e-3:
        b_star = 1e-3
    ita = math.degrees(math.atan((l - 50.0) / b_star))
    label = _ita_to_label(ita)
    message = (
        f"Assistive ITA estimate {ita:.1f} mapped to {label}. "
        "Please confirm or correct this; it is not a medical result."
    )
    if used_fallback:
        message += " Few skin-like pixels were found, so the center crop mean was used."
    return label, ita, used_fallback, message
