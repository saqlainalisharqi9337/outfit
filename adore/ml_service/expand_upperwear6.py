"""Add public hoodie/top/gown images into the existing upperwear6 splits.

Does not wipe shirt/t-shirt/jacket/dress copies already on disk.
Sources: HuggingFace secondhand clothing set, fashion-product extras,
and Alexey Grigorev clothing-dataset (zip).
"""

from __future__ import annotations

import csv
import json
import random
import shutil
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
OPEN_DIR = ROOT / "datasets" / "open_clothing"
OUT = ROOT / "datasets" / "upperwear6"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
CLASSES = ("shirt", "t-shirt", "hoodie", "jacket", "top", "dress")
CAPS = {"train": 1200, "val": 180, "test": 180}

SECONDHAND_MAP = {
    "dress": "dress",
    "night gown": "dress",
    "nightgown": "dress",
    "jacket": "jacket",
    "rain jacket": "jacket",
    "winter jacket": "jacket",
    "denim jacket": "jacket",
    "outerwear": "jacket",
    "blazer": "jacket",
    "t-shirt": "t-shirt",
    "shirt": "shirt",
    "hoodie": "hoodie",
    "top": "top",
    "tank top": "top",
    "tank top ": "top",
    "training top": "top",
    "tunic": "top",
    "blouse": "top",
}

HF_EXTRA_MAP = {
    "sweatshirts": "hoodie",
    "hoodies": "hoodie",
    "tops": "top",
    "tunics": "top",
    "shrugs": "top",
    "kurtis": "top",
    "gowns": "dress",
    "dresses": "dress",
    "jackets": "jacket",
    "blazers": "jacket",
    "rain jacket": "jacket",
    "nehru jackets": "jacket",
    "sports jackets": "jacket",
}

GRIGOREV_MAP = {
    "t-shirt": "t-shirt",
    "shirt": "shirt",
    "polo": "shirt",
    "hoodie": "hoodie",
    "outwear": "jacket",
    "blazer": "jacket",
    "top": "top",
    "blouse": "top",
    "dress": "dress",
}
GRIGOREV_ZIP = (
    "https://github.com/alexeygrigorev/clothing-dataset/archive/refs/heads/master.zip"
)


def _count(split: str, name: str) -> int:
    folder = OUT / split / name
    if not folder.is_dir():
        return 0
    return sum(1 for p in folder.iterdir() if p.is_file() and p.suffix.lower() in EXTS)


def _need(name: str) -> dict[str, int]:
    return {split: max(0, CAPS[split] - _count(split, name)) for split in CAPS}


def _save_pil(image: Image.Image, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        return False
    try:
        image.convert("RGB").save(dest, quality=90)
        return True
    except Exception:
        return False


def collect_secondhand(limit_per_class: dict[str, int] | None = None) -> dict[str, int]:
    limits = limit_per_class or {
        "hoodie": 900,
        "top": 900,
        "dress": 500,
        "jacket": 300,
        "shirt": 200,
        "t-shirt": 200,
    }
    added: dict[str, int] = defaultdict(int)
    try:
        from datasets import load_dataset
    except Exception as exc:  # noqa: BLE001
        print("huggingface datasets unavailable:", exc)
        return added
    out_root = OPEN_DIR / "secondhand_upperwear"
    try:
        print("loading wargoninnovation/clothingdatasetsecondhand")
        ds = load_dataset(
            "wargoninnovation/clothingdatasetsecondhand",
            split="train",
            streaming=True,
        )
    except Exception as exc:  # noqa: BLE001
        print("secondhand dataset skipped:", exc)
        return added
    names = None
    counts: dict[str, int] = defaultdict(int)
    scanned = 0
    for row in ds:
        scanned += 1
        if all(counts[c] >= limits[c] for c in CLASSES):
            break
        raw = row.get("type")
        if names is None:
            feat = getattr(ds, "features", None)
            try:
                names = feat["type"].names
            except Exception:
                names = None
        if isinstance(raw, int) and names:
            raw = names[raw]
        raw = str(raw or "").strip().lower()
        label = SECONDHAND_MAP.get(raw)
        if label is None or counts[label] >= limits.get(label, 0):
            continue
        image = row.get("image")
        if image is None:
            continue
        dest = out_root / label / f"sh_{counts[label]:04d}.jpg"
        if _save_pil(image, dest):
            counts[label] += 1
            added[label] += 1
        if scanned % 2000 == 0:
            print("secondhand scanned", scanned, dict(counts))
    print("secondhand done", dict(counts), "scanned", scanned)
    return added


def collect_hf_extra(limit_per_class: int = 800) -> dict[str, int]:
    added: dict[str, int] = defaultdict(int)
    try:
        from datasets import load_dataset
    except Exception as exc:  # noqa: BLE001
        print("huggingface datasets unavailable:", exc)
        return added
    out_root = OPEN_DIR / "fashion_product_small"
    try:
        print("loading ashraq/fashion-product-images-small extras")
        ds = load_dataset("ashraq/fashion-product-images-small", split="train")
    except Exception as exc:  # noqa: BLE001
        print("HF extras skipped:", exc)
        return added
    counts: dict[str, int] = defaultdict(int)
    for name in CLASSES:
        counts[name] = len(list((out_root / name).glob("*.jpg"))) if (out_root / name).is_dir() else 0
    saved = 0
    for row in ds:
        if all(counts[c] >= limit_per_class for c in ("hoodie", "top", "dress", "jacket")):
            break
        raw = str(row.get("articleType") or "").strip().lower()
        label = HF_EXTRA_MAP.get(raw)
        if label is None or counts[label] >= limit_per_class:
            continue
        image = row.get("image")
        if image is None:
            continue
        dest = out_root / label / f"hf2_{counts[label]:04d}.jpg"
        if _save_pil(image, dest):
            counts[label] += 1
            added[label] += 1
            saved += 1
        if saved and saved % 200 == 0:
            print("hf extra", dict(counts))
    print("hf extra done", dict(counts))
    return added


def download_grigorev() -> Path | None:
    dest = OPEN_DIR / "clothing-dataset-master"
    csv_path = dest / "images.csv"
    if csv_path.is_file() and (dest / "images").is_dir():
        print("grigorev already present")
        return dest
    zip_path = OPEN_DIR / "clothing-dataset-master.zip"
    OPEN_DIR.mkdir(parents=True, exist_ok=True)
    try:
        print("downloading Grigorev clothing-dataset zip")
        req = urllib.request.Request(GRIGOREV_ZIP, headers={"User-Agent": "AdoreFYP/1.0"})
        with urllib.request.urlopen(req, timeout=120) as resp, zip_path.open("wb") as out:
            shutil.copyfileobj(resp, out)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(OPEN_DIR)
        # github zip nests clothing-dataset-master/
        if csv_path.is_file():
            return dest
        nested = next(OPEN_DIR.glob("clothing-dataset*/images.csv"), None)
        if nested:
            return nested.parent
    except Exception as exc:  # noqa: BLE001
        print("grigorev zip skipped:", exc)
    return dest if csv_path.is_file() else None


def collect_grigorev(root: Path) -> dict[str, list[Path]]:
    by: dict[str, list[Path]] = defaultdict(list)
    csv_path = root / "images.csv"
    img_dir = root / "images"
    if not csv_path.is_file() or not img_dir.is_dir():
        return by
    with csv_path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            raw = (row.get("label") or "").strip().lower()
            label = GRIGOREV_MAP.get(raw)
            if not label:
                continue
            image_id = (row.get("image") or "").strip()
            path = img_dir / f"{image_id}.jpg"
            if path.is_file():
                by[label].append(path)
    print("grigorev counts", {k: len(v) for k, v in by.items()})
    return by


def _copy(src: Path, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        return False
    try:
        dest.hardlink_to(src)
        return True
    except OSError:
        try:
            shutil.copy2(src, dest)
            return True
        except OSError:
            return False


def absorb(files: list[Path], label: str, prefix: str) -> dict[str, int]:
    rng = random.Random(6 + len(prefix))
    rows = list(files)
    rng.shuffle(rows)
    need = _need(label)
    placed = {"train": 0, "val": 0, "test": 0}
    # Fill val/test first so evaluation isn't starved, then train.
    order = ["val", "test", "train"]
    i = 0
    for split in order:
        want = need[split]
        while want > 0 and i < len(rows):
            src = rows[i]
            i += 1
            dest = OUT / split / label / f"{prefix}_{i:04d}{src.suffix.lower() or '.jpg'}"
            if _copy(src, dest):
                placed[split] += 1
                want -= 1
    print("absorb", label, prefix, placed, "remaining sources", max(0, len(rows) - i))
    return placed


def existing_open_files(folder: Path, prefixes: tuple[str, ...] | None = None) -> list[Path]:
    if not folder.is_dir():
        return []
    files = [p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in EXTS]
    if prefixes:
        files = [p for p in files if p.name.startswith(prefixes)]
    return files


def main() -> int:
    OPEN_DIR.mkdir(parents=True, exist_ok=True)
    print("current counts")
    for name in CLASSES:
        print(" ", name, {s: _count(s, name) for s in CAPS})

    collect_secondhand()
    collect_hf_extra()
    grig = download_grigorev()
    grig_by = collect_grigorev(grig) if grig else {}

    for name in CLASSES:
        absorb(existing_open_files(OPEN_DIR / "secondhand_upperwear" / name), name, "sh")
        absorb(
            existing_open_files(OPEN_DIR / "fashion_product_small" / name, ("hf2_",)),
            name,
            "hf2",
        )
        absorb(grig_by.get(name, []), name, "gr")

    report_path = OUT / "dataset_report.json"
    report = {}
    if report_path.is_file():
        report = json.loads(report_path.read_text(encoding="utf-8"))
    report["expanded"] = {name: {s: _count(s, name) for s in CAPS} for name in CLASSES}
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("expanded", report["expanded"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
