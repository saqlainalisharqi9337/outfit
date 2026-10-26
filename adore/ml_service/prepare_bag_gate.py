"""Build bag vs skirt vs flats training folders from open images.

Bags:
  * local Adore ``accessories/bag``
  * Fashionpedia bag crops already in ``accessories_open``
  * COCO handbag / backpack / suitcase boxes
    (https://huggingface.co/datasets/detection-datasets/coco )
  * optional Hugging Face luggage/handbag harvest

Hard negatives (the two live mistakes):
  * local ``bottomwear/skirt``
  * local ``footwear/flats``

    .venv\\Scripts\\python.exe prepare_bag_gate.py
"""

from __future__ import annotations

import argparse
import random
import shutil
from collections import defaultdict
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
LOCAL = Path(r"D:\fyp project\dataset")
OPEN = LOCAL / "accessories_open"
OUT = LOCAL / "bag_gate"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def _copy_folder(src: Path, dest_dir: Path, prefix: str, limit: int) -> int:
    if not src.is_dir():
        return 0
    dest_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    files = [p for p in src.rglob("*") if p.is_file() and p.suffix.lower() in EXTS]
    files.sort(key=lambda p: p.name)
    for path in files:
        if n >= limit:
            break
        dest = dest_dir / f"{prefix}_{n:05d}{path.suffix.lower()}"
        if not dest.exists():
            shutil.copy2(path, dest)
        n += 1
    return n


def copy_local(limit: int) -> dict[str, int]:
    counts: dict[str, int] = {}
    bags = 0
    for split in ("train", "val", "test"):
        bags += _copy_folder(
            LOCAL / split / split / "accessories" / "bag",
            OUT / "pool" / "bag",
            f"local_{split}",
            limit,
        )
        if bags >= limit:
            break
    counts["bag_local"] = min(bags, limit)
    counts["skirt"] = _copy_folder(
        LOCAL / "train" / "train" / "bottomwear" / "skirt",
        OUT / "pool" / "skirt",
        "local_skirt",
        limit,
    )
    counts["flats"] = _copy_folder(
        LOCAL / "train" / "train" / "footwear" / "flats",
        OUT / "pool" / "flats",
        "local_flats",
        limit,
    )
    extra = OPEN / "pool" / "bag"
    counts["bag_fashionpedia"] = _copy_folder(extra, OUT / "pool" / "bag", "fp", limit)
    for split in ("train", "val", "test"):
        counts["bag_fashionpedia"] += _copy_folder(
            OPEN / split / "bag", OUT / "pool" / "bag", f"fp_{split}", limit
        )
    return counts


def from_coco(limit: int, scan_limit: int) -> int:
    try:
        from datasets import load_dataset
    except ImportError:
        print("datasets missing; skip COCO handbags")
        return 0
    wanted = {"handbag", "backpack", "suitcase"}
    dest = OUT / "pool" / "bag"
    dest.mkdir(parents=True, exist_ok=True)
    existing_coco = len(list(dest.glob("coco_*")))
    if existing_coco >= min(400, limit):
        print(f"COCO skip, already {existing_coco} COCO bag crops")
        return 0
    print("Streaming COCO handbags/backpacks from Hugging Face…", flush=True)
    saved = 0
    seen = 0
    try:
        ds = load_dataset("detection-datasets/coco", split="val", streaming=True)
    except Exception as exc:  # noqa: BLE001
        print("COCO load failed:", exc, flush=True)
        return 0
    for row in ds:
        seen += 1
        if seen > scan_limit or existing_coco + saved >= min(400, limit):
            break
        objects = row.get("objects") or {}
        cats = objects.get("category") or []
        boxes = objects.get("bbox") or []
        image = row.get("image")
        if image is None:
            continue
        image = image.convert("RGB")
        width, height = image.size
        for cat, bbox in zip(cats, boxes):
            name = str(cat).lower()
            if name not in wanted:
                continue
            if len(bbox) != 4:
                continue
            x1, y1, x2, y2 = (float(v) for v in bbox)
            if x2 - x1 < 24 or y2 - y1 < 24:
                continue
            pad = 0.12
            bw, bh = x2 - x1, y2 - y1
            left = max(0, int(x1 - pad * bw))
            top = max(0, int(y1 - pad * bh))
            right = min(width, int(x2 + pad * bw))
            bottom = min(height, int(y2 + pad * bh))
            crop = image.crop((left, top, right, bottom))
            dest_path = dest / f"coco_{seen}_{saved}.jpg"
            crop.save(dest_path, format="JPEG", quality=90)
            saved += 1
            if existing_coco + saved >= min(400, limit):
                break
        if seen % 300 == 0:
            print(f"  coco scanned {seen}, extra bags {saved}", flush=True)
    print(f"COCO bags added: {saved} (scanned {seen})", flush=True)
    return saved


def split_pool(seed: int = 11) -> dict[str, dict[str, int]]:
    rng = random.Random(seed)
    report: dict[str, dict[str, int]] = {"train": {}, "val": {}, "test": {}}
    for leaf in ("bag", "skirt", "flats"):
        files = [
            p
            for p in (OUT / "pool" / leaf).glob("*")
            if p.is_file() and p.suffix.lower() in EXTS
        ]
        files.sort(key=lambda p: p.name)
        rng.shuffle(files)
        n = len(files)
        n_test = max(20, int(n * 0.12)) if n >= 80 else max(6, n // 6)
        n_val = max(20, int(n * 0.12)) if n >= 80 else max(6, n // 6)
        test, val, train = files[:n_test], files[n_test : n_test + n_val], files[n_test + n_val :]
        for split, group in (("test", test), ("val", val), ("train", train)):
            dest = OUT / split / leaf
            dest.mkdir(parents=True, exist_ok=True)
            for src in group:
                target = dest / src.name
                if not target.exists():
                    shutil.copy2(src, target)
            report[split][leaf] = len(group)
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=900)
    ap.add_argument("--coco-scan", type=int, default=2500)
    ap.add_argument("--skip-coco", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    print("local:", copy_local(args.limit), flush=True)
    if not args.skip_coco:
        try:
            print("coco:", from_coco(args.limit, args.coco_scan), flush=True)
        except Exception as exc:  # noqa: BLE001
            print("coco failed:", exc, flush=True)
    print("splits:", split_pool(), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
