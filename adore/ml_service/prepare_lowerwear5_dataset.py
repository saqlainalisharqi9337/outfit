"""Build 5-class lowerwear training set: trousers, shorts, skirt, shalwar, leggings.

Sources:
  1. Local Adore bottomwear folders
  2. HuggingFace ashraq/fashion-product-images-small
  3. Grigorev clothing-dataset if already on disk

Also writes degraded (blur / dark / noisy / tight-crop) copies so the
model sees both clean product shots and unclear real-world photos.

Does not overwrite trousers_gate or trousers_shorts_skirt keras files.
"""

from __future__ import annotations

import csv
import io
import json
import random
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parent
LOCAL = Path(r"D:\fyp project\dataset")
OPEN_DIR = ROOT / "datasets" / "open_clothing"
OUT = ROOT / "datasets" / "lowerwear5"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

CLASSES = ("trousers", "shorts", "skirt", "shalwar", "leggings")

HF_MAP = {
    "jeans": "trousers",
    "trousers": "trousers",
    "track pants": "trousers",
    "palazzos": "trousers",
    "capris": "trousers",
    "lounge pants": "trousers",
    "lounge shorts": "shorts",
    "shorts": "shorts",
    "skirts": "skirt",
    "leggings": "leggings",
    "jeggings": "leggings",
    "tights": "leggings",
    "salwar": "shalwar",
    "salwar and dupatta": "shalwar",
    "patiala": "shalwar",
    "churidar": "shalwar",
    "dhoti pants": "shalwar",
}

GRIGOREV_MAP = {
    "pants": "trousers",
    "shorts": "shorts",
    "skirt": "skirt",
}

LOCAL_SOURCES: list[tuple[str, str]] = [
    ("train/train/bottomwear/pants", "trousers"),
    ("val/val/bottomwear/pants", "trousers"),
    ("test/test/bottomwear/pants", "trousers"),
    ("train/train/bottomwear/shorts", "shorts"),
    ("val/val/bottomwear/shorts", "shorts"),
    ("test/test/bottomwear/shorts", "shorts"),
    ("train/train/bottomwear/skirt", "skirt"),
    ("val/val/bottomwear/skirt", "skirt"),
    ("test/test/bottomwear/skirt", "skirt"),
    ("trousers_gate/train/trousers", "trousers"),
    ("trousers_gate/val/trousers", "trousers"),
    ("skirt_gate/train/skirt", "skirt"),
    ("skirt_gate/val/skirt", "skirt"),
]

MAJORITY_CAP = {"trousers": 1200, "shorts": 1200, "skirt": 1200, "shalwar": 900, "leggings": 900}
VAL_CAP = 180
TEST_CAP = 180
UNCLEAR_FRACTION = 0.22


def _files(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    out = [p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in EXTS]
    out.sort(key=lambda p: p.as_posix())
    return out


def collect_local() -> dict[str, list[Path]]:
    by: dict[str, list[Path]] = defaultdict(list)
    for rel, label in LOCAL_SOURCES:
        by[label].extend(_files(LOCAL / rel))
    return by


def collect_hf() -> dict[str, list[Path]]:
    by: dict[str, list[Path]] = defaultdict(list)
    out_root = OPEN_DIR / "fashion_product_lowerwear"
    try:
        from datasets import load_dataset
    except Exception as exc:  # noqa: BLE001
        print("huggingface datasets unavailable:", exc)
        return by
    try:
        print("loading ashraq/fashion-product-images-small")
        ds = load_dataset("ashraq/fashion-product-images-small", split="train")
    except Exception as exc:  # noqa: BLE001
        print("HF skipped:", exc)
        return by
    counts: dict[str, int] = defaultdict(int)
    minority = {"shalwar", "leggings"}
    cap = {c: (800 if c in minority else 500) for c in CLASSES}
    saved = 0
    for row in ds:
        if all(counts[c] >= cap[c] for c in CLASSES):
            break
        raw = str(row.get("articleType") or "").strip().lower()
        label = HF_MAP.get(raw)
        if label is None or counts[label] >= cap[label]:
            continue
        image = row.get("image")
        if image is None:
            continue
        dest_dir = out_root / label
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"hf_{counts[label]:04d}.jpg"
        try:
            image.convert("RGB").save(dest, quality=90)
        except Exception:
            continue
        by[label].append(dest)
        counts[label] += 1
        saved += 1
        if saved % 200 == 0:
            print("hf lowerwear saved", dict(counts))
    print("hf lowerwear done", dict(counts))
    return by


def collect_grigorev() -> dict[str, list[Path]]:
    by: dict[str, list[Path]] = defaultdict(list)
    root = OPEN_DIR / "clothing-dataset-master"
    csv_path = root / "images.csv"
    img_dir = root / "images"
    if not csv_path.is_file() or not img_dir.is_dir():
        print("grigorev not on disk, skipped")
        return by
    with csv_path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            label = GRIGOREV_MAP.get((row.get("label") or "").strip().lower())
            if not label:
                continue
            image_id = (row.get("image") or "").strip()
            path = img_dir / f"{image_id}.jpg"
            if path.is_file():
                by[label].append(path)
    print("grigorev", {k: len(v) for k, v in by.items()})
    return by


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
        small = out.resize((max(16, int(w * scale)), max(16, int(h * scale))), Image.Resampling.BILINEAR)
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


def split_counts(n: int, label: str) -> tuple[int, int, int]:
    train_cap = MAJORITY_CAP.get(label, 1200)
    if n >= train_cap + VAL_CAP + TEST_CAP:
        return train_cap, VAL_CAP, TEST_CAP
    test = min(TEST_CAP, max(8, n // 8))
    val = min(VAL_CAP, max(8, n // 8))
    if test + val >= n:
        test = max(4, n // 10)
        val = max(4, n // 10)
    train = n - val - test
    if train < 16:
        train = max(8, n - 8)
        val = max(2, (n - train) // 2)
        test = n - train - val
    return train, val, test


def copy_image(src: Path, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(src) as im:
            ImageOps.exif_transpose(im.convert("RGB")).save(dest, quality=90)
        return True
    except Exception:
        return False


def add_unclear(split_dir: Path, rng: random.Random) -> int:
    added = 0
    for cls in CLASSES:
        folder = split_dir / cls
        originals = _files(folder)
        frac = 0.45 if cls in {"shalwar", "leggings"} else UNCLEAR_FRACTION
        k = max(1, int(len(originals) * frac)) if originals else 0
        for i, src in enumerate(originals[:k]):
            dest = folder / f"unclear_{i:04d}.jpg"
            try:
                with Image.open(src) as im:
                    make_unclear(ImageOps.exif_transpose(im.convert("RGB")), rng).save(
                        dest, quality=rng.randint(55, 82)
                    )
                added += 1
            except Exception:
                continue
    return added


def main() -> int:
    rng = random.Random(21)
    pooled: dict[str, list[Path]] = defaultdict(list)
    for src in (collect_local(), collect_hf(), collect_grigorev()):
        for label, rows in src.items():
            pooled[label].extend(rows)
    unique: dict[str, list[Path]] = {}
    for label, rows in pooled.items():
        seen: set[str] = set()
        keep = []
        for path in rows:
            key = str(path.resolve()) if path.exists() else str(path)
            if key in seen:
                continue
            seen.add(key)
            keep.append(path)
        rng.shuffle(keep)
        unique[label] = keep
        print(f"available {label}: {len(keep)}")

    if OUT.exists():
        import shutil

        shutil.rmtree(OUT)
    report = {"classes": {}, "sources": "local+hf+grigorev", "unclearFraction": UNCLEAR_FRACTION}
    for label in CLASSES:
        files = unique.get(label, [])
        train_n, val_n, test_n = split_counts(len(files), label)
        chunks = {
            "train": files[:train_n],
            "val": files[train_n : train_n + val_n],
            "test": files[train_n + val_n : train_n + val_n + test_n],
        }
        copied = {}
        for split, rows in chunks.items():
            n = 0
            for i, src in enumerate(rows):
                dest = OUT / split / label / f"{label}_{i:04d}.jpg"
                if copy_image(src, dest):
                    n += 1
            copied[split] = n
        report["classes"][label] = {
            "available": len(files),
            **copied,
        }
        print(label, report["classes"][label])

    unclear = {
        "train": add_unclear(OUT / "train", rng),
        "val": add_unclear(OUT / "val", rng),
        "test": add_unclear(OUT / "test", rng),
    }
    report["unclearAdded"] = unclear
    print("unclear copies", unclear)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "dataset_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
