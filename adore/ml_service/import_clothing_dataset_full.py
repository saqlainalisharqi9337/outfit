"""Import full CC0 clothing-dataset (GitHub) into Adore folder layout."""

from __future__ import annotations

import argparse
import csv
import random
import shutil
from collections import Counter
from pathlib import Path

SRC_DEFAULT = Path(r"D:\fyp project\open_data\clothing-dataset-master")
DST_DEFAULT = Path(r"D:\fyp project\dataset")
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

# open label -> (family, leaf)
MAP = {
    "shirt": ("upperwear", "shirt"),
    "t-shirt": ("upperwear", "tshirt"),
    "longsleeve": ("upperwear", "shirt"),
    "outwear": ("upperwear", "jacket"),
    "blazer": ("upperwear", "jacket"),
    "hoodie": ("upperwear", "jacket"),
    "top": ("upperwear", "tshirt"),
    "polo": ("upperwear", "tshirt"),
    "blouse": ("upperwear", "shirt"),
    "undershirt": ("upperwear", "tshirt"),
    "pants": ("bottomwear", "pants"),
    "shorts": ("bottomwear", "shorts"),
    "skirt": ("bottomwear", "skirt"),
    "dress": ("one-piece", "dress"),
    "hat": ("accessories", "hat"),
    "shoes": ("footwear", "shoes"),
}


def split_three(paths: list[Path], seed: int = 7) -> dict[str, list[Path]]:
    rng = random.Random(seed)
    rows = list(paths)
    rng.shuffle(rows)
    n = len(rows)
    n_test = max(1, int(n * 0.10)) if n >= 10 else 0
    n_val = max(1, int(n * 0.10)) if n >= 10 else 0
    return {
        "test": rows[:n_test],
        "val": rows[n_test : n_test + n_val],
        "train": rows[n_test + n_val :],
    }


def collect(src: Path) -> dict[str, list[Path]]:
    """Support both folder layout and images.csv + images/."""
    out: dict[str, list[Path]] = {}
    csv_path = src / "images.csv"
    images_dir = src / "images"
    if csv_path.is_file() and images_dir.is_dir():
        with csv_path.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                label = (row.get("label") or "").strip().lower()
                image_id = (row.get("image") or "").strip()
                if label not in MAP or not image_id:
                    continue
                path = images_dir / f"{image_id}.jpg"
                if not path.is_file():
                    path = images_dir / f"{image_id}.jpeg"
                if not path.is_file():
                    continue
                out.setdefault(label, []).append(path)
        return out

    for split in ("train", "validation", "test", "val"):
        base = src / split
        if not base.is_dir():
            continue
        for folder in base.iterdir():
            if not folder.is_dir():
                continue
            label = folder.name.lower()
            if label not in MAP:
                continue
            for p in folder.rglob("*"):
                if p.is_file() and p.suffix.lower() in EXTS:
                    out.setdefault(label, []).append(p)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=SRC_DEFAULT)
    ap.add_argument("--dst", type=Path, default=DST_DEFAULT)
    ap.add_argument("--prefix", default="fullopen_")
    args = ap.parse_args()

    grouped = collect(args.src)
    print("labels found:", {k: len(v) for k, v in sorted(grouped.items())})
    copied = 0
    counts: Counter[str] = Counter()
    for label, paths in grouped.items():
        family, leaf = MAP[label]
        parts = split_three(paths)
        for split, rows in parts.items():
            dest_dir = args.dst / split / split / family / leaf
            dest_dir.mkdir(parents=True, exist_ok=True)
            for i, src in enumerate(rows):
                dest = dest_dir / f"{args.prefix}{label}_{i:05d}{src.suffix.lower()}"
                if dest.exists():
                    continue
                shutil.copy2(src, dest)
                copied += 1
                counts[f"{family}/{leaf}"] += 1
    print("copied", copied, dict(counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
