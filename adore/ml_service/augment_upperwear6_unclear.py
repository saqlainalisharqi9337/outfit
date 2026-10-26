"""Add blurred/dark/noisy copies to the existing upperwear6 splits."""

from __future__ import annotations

import io
import json
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "datasets" / "upperwear6"
CLASSES = ("shirt", "t-shirt", "hoodie", "jacket", "top", "dress")
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
UNCLEAR = {"hoodie": 0.45, "top": 0.45, "default": 0.22}


def make_unclear(im: Image.Image, rng: random.Random) -> Image.Image:
    out = im.convert("RGB")
    w, h = out.size
    mode = rng.choice(("blur", "dark", "noise", "crop", "pixel", "glare"))
    if mode == "blur":
        out = out.filter(ImageFilter.GaussianBlur(radius=rng.uniform(1.4, 3.2)))
    elif mode == "dark":
        out = ImageEnhance.Brightness(out).enhance(rng.uniform(0.45, 0.72))
        out = ImageEnhance.Contrast(out).enhance(rng.uniform(0.7, 1.05))
    elif mode == "noise":
        arr = np.asarray(out).astype(np.int16)
        noise = rng.randint(12, 28)
        arr = arr + np.random.randint(-noise, noise + 1, size=arr.shape)
        out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    elif mode == "crop":
        left = int(w * rng.uniform(0.0, 0.18))
        top = int(h * rng.uniform(0.0, 0.22))
        right = int(w * rng.uniform(0.82, 1.0))
        bottom = int(h * rng.uniform(0.78, 1.0))
        out = out.crop((left, top, max(left + 32, right), max(top + 32, bottom)))
        out = out.resize((w, h), Image.Resampling.BILINEAR)
    elif mode == "pixel":
        scale = rng.uniform(0.22, 0.42)
        small = out.resize(
            (max(16, int(w * scale)), max(16, int(h * scale))),
            Image.Resampling.BILINEAR,
        )
        out = small.resize((w, h), Image.Resampling.NEAREST)
    else:
        out = ImageEnhance.Color(out).enhance(rng.uniform(0.35, 0.85))
        overlay = Image.new("RGB", out.size, (255, 255, 230))
        out = Image.blend(out, overlay, rng.uniform(0.12, 0.28))
    if rng.random() < 0.45:
        buf = io.BytesIO()
        out.save(buf, format="JPEG", quality=rng.randint(22, 48))
        buf.seek(0)
        out = Image.open(buf).convert("RGB")
    return ImageOps.exif_transpose(out)


def main() -> int:
    if not (DATA / "train").is_dir():
        raise SystemExit("datasets/upperwear6 missing")
    rng = random.Random(6)
    added = {}
    for split in ("train", "val", "test"):
        n = 0
        for cls in CLASSES:
            folder = DATA / split / cls
            if not folder.is_dir():
                continue
            originals = [
                p
                for p in folder.iterdir()
                if p.is_file()
                and p.suffix.lower() in EXTS
                and not p.name.startswith("unclear_")
            ]
            frac = UNCLEAR.get(cls, UNCLEAR["default"])
            k = max(1, int(len(originals) * frac)) if originals else 0
            for i, src in enumerate(originals[:k]):
                dest = folder / f"unclear_{i:04d}.jpg"
                if dest.exists():
                    continue
                try:
                    with Image.open(src) as im:
                        make_unclear(
                            ImageOps.exif_transpose(im.convert("RGB")), rng
                        ).save(dest, quality=rng.randint(55, 82))
                    n += 1
                except Exception:
                    continue
        added[split] = n
        print(split, "unclear added", n)
    report_path = DATA / "dataset_report.json"
    report = {}
    if report_path.is_file():
        report = json.loads(report_path.read_text(encoding="utf-8"))
    report["unclearAdded"] = added
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("done", added)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
