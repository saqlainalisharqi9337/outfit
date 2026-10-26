"""Import open CC0 clothing-dataset-small into Adore dataset layout.

Source (CC0): https://github.com/alexeygrigorev/clothing-dataset-small

Maps:
  shirt→upperwear/shirt, t-shirt→upperwear/tshirt, outwear→upperwear/jacket,
  pants→bottomwear/pants, shorts→bottomwear/shorts, skirt→bottomwear/skirt,
  dress→one-piece/dress, hat→accessories/hat, shoes→footwear/shoes
"""

from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path

SRC_DEFAULT = Path(r"D:\fyp project\open_data\clothing-dataset-small-master")
DST_DEFAULT = Path(r"D:\fyp project\dataset")
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

# open_class -> (family, leaf)
MAP = {
    "shirt": ("upperwear", "shirt"),
    "t-shirt": ("upperwear", "tshirt"),
    "outwear": ("upperwear", "jacket"),
    "pants": ("bottomwear", "pants"),
    "shorts": ("bottomwear", "shorts"),
    "skirt": ("bottomwear", "skirt"),
    "dress": ("one-piece", "dress"),
    "hat": ("accessories", "hat"),
    "shoes": ("footwear", "shoes"),
}


def collect_open(root: Path) -> dict[str, list[Path]]:
    out: dict[str, list[Path]] = {k: [] for k in MAP}
    for split in ("train", "validation", "test"):
        base = root / split
        if not base.is_dir():
            continue
        for name, paths in out.items():
            folder = base / name
            if not folder.is_dir():
                continue
            for p in folder.rglob("*"):
                if p.is_file() and p.suffix.lower() in EXTS:
                    paths.append(p)
    return out


def split_three(paths: list[Path], seed: int = 42) -> dict[str, list[Path]]:
    rng = random.Random(seed)
    rows = list(paths)
    rng.shuffle(rows)
    n = len(rows)
    n_test = max(1, int(n * 0.10)) if n >= 10 else max(0, n // 10)
    n_val = max(1, int(n * 0.10)) if n >= 10 else max(0, n // 10)
    return {
        "test": rows[:n_test],
        "val": rows[n_test : n_test + n_val],
        "train": rows[n_test + n_val :],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=SRC_DEFAULT)
    ap.add_argument("--dst", type=Path, default=DST_DEFAULT)
    ap.add_argument("--prefix", default="open_")
    args = ap.parse_args()

    grouped = collect_open(args.src)
    copied = 0
    for open_name, (family, leaf) in MAP.items():
        paths = grouped.get(open_name) or []
        print(f"{open_name:10s} -> {family}/{leaf}: {len(paths)}")
        parts = split_three(paths)
        for split, rows in parts.items():
            dest_dir = args.dst / split / split / family / leaf
            dest_dir.mkdir(parents=True, exist_ok=True)
            for i, src in enumerate(rows):
                dest = dest_dir / f"{args.prefix}{open_name}_{i:05d}{src.suffix.lower()}"
                if dest.exists():
                    continue
                shutil.copy2(src, dest)
                copied += 1
    print(f"copied {copied} new files into {args.dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
