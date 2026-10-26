"""Build the 6-class upperwear+dress training set.

Sources (all redistributable):
  1. Local Adore folders under D:\\fyp project\\dataset
  2. Alexey Grigorev clothing-dataset (free for any use, incl. commercial)
     https://github.com/alexeygrigorev/clothing-dataset

Does not touch trousers/skirt/footwear specialists.
"""

from __future__ import annotations

import csv
import io
import json
import random
import shutil
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOCAL = Path(r"D:\fyp project\dataset")
OPEN_DIR = ROOT / "datasets" / "open_clothing"
OUT = ROOT / "datasets" / "upperwear6"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

CLASSES = ("shirt", "t-shirt", "hoodie", "jacket", "top", "dress")

GRIGOREV_ZIP = (
    "https://github.com/alexeygrigorev/clothing-dataset/archive/refs/heads/master.zip"
)
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

LOCAL_SOURCES: list[tuple[str, str, str]] = [
    ("train/train/upperwear/shirt", "shirt"),
    ("val/val/upperwear/shirt", "shirt"),
    ("test/test/upperwear/shirt", "shirt"),
    ("train/train/upperwear/tshirt", "t-shirt"),
    ("val/val/upperwear/tshirt", "t-shirt"),
    ("test/test/upperwear/tshirt", "t-shirt"),
    ("train/train/upperwear/jacket", "jacket"),
    ("val/val/upperwear/jacket", "jacket"),
    ("test/test/upperwear/jacket", "jacket"),
    ("train/train/one-piece/dress", "dress"),
    ("val/val/one-piece/dress", "dress"),
    ("test/test/one-piece/dress", "dress"),
    ("shirt_gate/train/shirt", "shirt"),
    ("shirt_gate/val/shirt", "shirt"),
    ("tshirt_gate/train/t-shirt", "t-shirt"),
    ("tshirt_gate/val/t-shirt", "t-shirt"),
    ("jacket_gate/train/jacket", "jacket"),
    ("jacket_gate/val/jacket", "jacket"),
    ("shirt_gate/train/dress", "dress"),
    ("shirt_gate/val/dress", "dress"),
]

TRAIN_CAP = 1200
VAL_CAP = 180
TEST_CAP = 180


def _files(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    out = [p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in EXTS]
    out.sort(key=lambda p: p.as_posix())
    return out


def download_grigorev() -> Path | None:
    dest = OPEN_DIR / "clothing-dataset-master"
    csv_path = dest / "images.csv"
    if csv_path.is_file() and (dest / "images").is_dir():
        print("open dataset already present", dest)
        return dest
    OPEN_DIR.mkdir(parents=True, exist_ok=True)
    try:
        import subprocess

        print("cloning clothing-dataset")
        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "https://github.com/alexeygrigorev/clothing-dataset.git",
                str(dest),
            ],
            check=True,
            timeout=180,
        )
        if csv_path.is_file():
            return dest
    except Exception as exc:  # noqa: BLE001
        print("git clone skipped:", exc)
    return dest if csv_path.is_file() else None


def collect_hf_fashion(limit_per_class: int = 400) -> dict[str, list[Path]]:
    """ashraq/fashion-product-images-small — Kaggle fashion products, widely used."""
    by: dict[str, list[Path]] = defaultdict(list)
    mapping = {
        "shirts": "shirt",
        "tshirts": "t-shirt",
        "dresses": "dress",
        "jackets": "jacket",
        "tops": "top",
        "sweaters": "hoodie",
        "sweatshirts": "hoodie",
        "hoodies": "hoodie",
        "tunics": "top",
        "kurtas": "shirt",
        "kurta sets": "dress",
        "gowns": "dress",
        "blazers": "jacket",
        "waistcoat": "jacket",
        "shrugs": "top",
        "dupatta": None,
    }
    out_root = OPEN_DIR / "fashion_product_small"
    try:
        from datasets import load_dataset
    except Exception as exc:  # noqa: BLE001
        print("huggingface datasets unavailable:", exc)
        return by
    try:
        print("loading ashraq/fashion-product-images-small")
        ds = load_dataset("ashraq/fashion-product-images-small", split="train")
    except Exception as extra:  # noqa: BLE001
        print("HF fashion-product-images-small skipped:", extra)
        return by
    counts: dict[str, int] = defaultdict(int)
    saved = 0
    for row in ds:
        if all(counts[c] >= limit_per_class for c in CLASSES):
            break
        raw = str(row.get("articleType") or row.get("label") or "").strip().lower()
        label = mapping.get(raw)
        if label is None or counts[label] >= limit_per_class:
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
            print("hf saved", dict(counts))
    print("hf done", dict(counts))
    return by


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
    return by


def collect_local() -> dict[str, list[Path]]:
    by: dict[str, list[Path]] = defaultdict(list)
    seen: set[str] = set()
    for rel, label in LOCAL_SOURCES:
        for path in _files(LOCAL / rel):
            key = path.as_posix().lower()
            if key in seen:
                continue
            seen.add(key)
            by[label].append(path)
    return by


def _copy(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        return
    try:
        dest.hardlink_to(src)
    except OSError:
        shutil.copy2(src, dest)


def write_splits(by_class: dict[str, list[Path]]) -> dict:
    random.seed(6)
    report = {"classes": {}, "splits": {"train": 0, "val": 0, "test": 0}, "sources": {}}
    if OUT.exists():
        shutil.rmtree(OUT)
    for name in CLASSES:
        files = list(dict.fromkeys(by_class.get(name, [])))
        random.shuffle(files)
        n = len(files)
        n_test = min(TEST_CAP, max(12, n // 8)) if n >= 80 else max(8, n // 5)
        n_val = min(VAL_CAP, max(12, n // 8)) if n >= 80 else max(8, n // 5)
        if n_test + n_val >= n:
            n_test = max(4, n // 6)
            n_val = max(4, n // 6)
        test = files[:n_test]
        val = files[n_test : n_test + n_val]
        train = files[n_test + n_val : n_test + n_val + TRAIN_CAP]
        report["classes"][name] = {
            "available": len(files),
            "train": len(train),
            "val": len(val),
            "test": len(test),
        }
        for split, rows in (("train", train), ("val", val), ("test", test)):
            for i, src in enumerate(rows):
                dest = OUT / split / name / f"{name}_{i:04d}{src.suffix.lower()}"
                _copy(src, dest)
                report["splits"][split] += 1
    (OUT / "dataset_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    local = collect_local()
    extra: dict[str, list[Path]] = defaultdict(list)
    cached = OPEN_DIR / "fashion_product_small"
    if cached.is_dir() and any(cached.iterdir()):
        print("using cached HF fashion_product_small")
        for name in CLASSES:
            extra[name].extend(_files(cached / name))
    else:
        for k, rows in collect_hf_fashion().items():
            extra[k].extend(rows)
    open_root = download_grigorev()
    if open_root is not None:
        for k, rows in collect_grigorev(open_root).items():
            extra[k].extend(rows)
    merged: dict[str, list[Path]] = defaultdict(list)
    for src in (local, extra):
        for k, rows in src.items():
            merged[k].extend(rows)
    report = write_splits(merged)
    report["openImages"] = {k: len(v) for k, v in extra.items()}
    report["localImages"] = {k: len(v) for k, v in local.items()}
    report["license"] = (
        "Grigorev clothing-dataset: free for any purpose including commercial. "
        "Local Adore product photos remain private training data."
    )
    (OUT / "dataset_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
