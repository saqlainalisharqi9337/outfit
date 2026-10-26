"""Build watch vs belt vs bag vs trousers folders from open images.

Watches / belts:
  * Fashionpedia crops (https://fashionpedia.github.io )
  * Hugging Face fashion-product-images (Watches / Belts)
  * existing Adore ``accessories_open`` belt crops

Hard negatives (the live mistakes):
  * local ``accessories/bag``
  * local ``bottomwear/pants``

    .venv\\Scripts\\python.exe prepare_watch_belt_gate.py
"""

from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path

from PIL import Image

LOCAL = Path(r"D:\fyp project\dataset")
OPEN = LOCAL / "accessories_open"
OUT = LOCAL / "watch_belt_gate"
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
    counts["belt_open"] = _copy_folder(
        OPEN / "pool" / "belt", OUT / "pool" / "belt", "fp", limit
    )
    for split in ("train", "val", "test"):
        counts["belt_open"] += _copy_folder(
            OPEN / split / "belt", OUT / "pool" / "belt", f"fp_{split}", limit
        )
    counts["watch_open"] = _copy_folder(
        OPEN / "pool" / "watch", OUT / "pool" / "watch", "fpw", limit
    )
    for split in ("train", "val", "test"):
        counts["watch_open"] += _copy_folder(
            OPEN / split / "watch", OUT / "pool" / "watch", f"fpw_{split}", limit
        )
    counts["bag"] = _copy_folder(
        LOCAL / "train" / "train" / "accessories" / "bag",
        OUT / "pool" / "bag",
        "local_bag",
        limit,
    )
    counts["trousers"] = _copy_folder(
        LOCAL / "train" / "train" / "bottomwear" / "pants",
        OUT / "pool" / "trousers",
        "local_pants",
        limit,
    )
    return counts


def _save_rgb(image: Image.Image, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(dest, format="JPEG", quality=90)


def _row_text(row: dict) -> str:
    parts = []
    for key in (
        "articleType",
        "subCategory",
        "masterCategory",
        "category",
        "label",
        "class",
        "objects",
    ):
        value = row.get(key)
        if value is not None:
            parts.append(str(value).lower())
    return " ".join(parts)


def from_fashion_products(limit: int, scan_limit: int) -> dict[str, int]:
    counts = {"watch": 0, "belt": 0}
    dest_watch = OUT / "pool" / "watch"
    dest_belt = OUT / "pool" / "belt"
    dest_watch.mkdir(parents=True, exist_ok=True)
    dest_belt.mkdir(parents=True, exist_ok=True)
    if len(list(dest_watch.glob("myntra_*"))) >= min(400, limit) and len(
        list(dest_belt.glob("myntra_*"))
    ) >= min(200, limit):
        print("fashion-product-images skip, already harvested")
        return counts
    try:
        from datasets import load_dataset
    except ImportError:
        print("datasets missing; skip fashion-product-images")
        return counts
    print("Streaming Hugging Face fashion-product-images-small…", flush=True)
    try:
        ds = load_dataset(
            "ashraq/fashion-product-images-small",
            split="train",
            streaming=True,
        )
    except Exception as exc:  # noqa: BLE001
        print("fashion-product-images load failed:", exc, flush=True)
        return counts
    seen = 0
    for row in ds:
        seen += 1
        if seen > scan_limit:
            break
        if counts["watch"] >= limit and counts["belt"] >= min(400, limit):
            break
        text = _row_text(row)
        leaf = None
        if "watch" in text and "belt" not in text:
            leaf = "watch"
        elif text.strip() == "belts" or " belt" in f" {text}" or text.startswith("belts"):
            if "bag" not in text and "watch" not in text:
                leaf = "belt"
        elif "articletype" in str(row).lower():
            article = str(row.get("articleType") or "").lower()
            if article == "watches":
                leaf = "watch"
            elif article == "belts":
                leaf = "belt"
        if leaf is None:
            article = str(row.get("articleType") or "").lower()
            if article == "watches":
                leaf = "watch"
            elif article == "belts":
                leaf = "belt"
        if leaf is None:
            continue
        if counts[leaf] >= (limit if leaf == "watch" else min(400, limit)):
            continue
        image = row.get("image")
        if image is None:
            continue
        dest = (dest_watch if leaf == "watch" else dest_belt) / f"myntra_{leaf}_{counts[leaf]:05d}.jpg"
        try:
            _save_rgb(image, dest)
            counts[leaf] += 1
        except Exception:  # noqa: BLE001
            continue
        if seen % 400 == 0:
            print(f"  scanned {seen}, {counts}", flush=True)
    print(f"fashion-product-images: {counts} (scanned {seen})", flush=True)
    return counts


def _save_crop(image: Image.Image, bbox: list[float], dest: Path, pad: float = 0.12) -> bool:
    width, height = image.size
    if len(bbox) != 4:
        return False
    x1, y1, x2, y2 = (float(v) for v in bbox)
    if x2 <= x1 or y2 <= y1:
        return False
    bw, bh = x2 - x1, y2 - y1
    x1 = max(0, x1 - pad * bw)
    y1 = max(0, y1 - pad * bh)
    x2 = min(width, x2 + pad * bw)
    y2 = min(height, y2 + pad * bh)
    if x2 - x1 < 18 or y2 - y1 < 18:
        return False
    crop = image.crop((int(x1), int(y1), int(x2), int(y2))).convert("RGB")
    dest.parent.mkdir(parents=True, exist_ok=True)
    crop.save(dest, format="JPEG", quality=90)
    return True


def from_fashionpedia(limit: int, scan_limit: int) -> dict[str, int]:
    counts = {"watch": 0, "belt": 0}
    dest_watch = OUT / "pool" / "watch"
    dest_belt = OUT / "pool" / "belt"
    dest_watch.mkdir(parents=True, exist_ok=True)
    dest_belt.mkdir(parents=True, exist_ok=True)
    existing_w = len(list(dest_watch.glob("fpdet_*")))
    existing_b = len(list(dest_belt.glob("fpdet_*")))
    if existing_w >= min(200, limit) and existing_b >= min(100, limit):
        print("Fashionpedia watch/belt skip, already harvested")
        return counts
    try:
        from datasets import load_dataset
        from app.fashionpedia_map import name_for_index
    except Exception as exc:  # noqa: BLE001
        print("Fashionpedia harvest skipped:", exc, flush=True)
        return counts
    wanted = {"watch": dest_watch, "belt": dest_belt}
    print("Streaming Fashionpedia val for watch/belt…", flush=True)
    try:
        ds = load_dataset("detection-datasets/fashionpedia", split="val", streaming=True)
    except Exception as exc:  # noqa: BLE001
        print("Fashionpedia load failed:", exc, flush=True)
        return counts
    seen = 0
    for row in ds:
        seen += 1
        if seen > scan_limit:
            break
        if counts["watch"] + existing_w >= min(400, limit) and counts["belt"] + existing_b >= min(200, limit):
            break
        objects = row.get("objects") or {}
        cats = objects.get("category") or []
        boxes = objects.get("bbox") or []
        image = row.get("image")
        if image is None:
            continue
        image = image.convert("RGB")
        for cat, bbox in zip(cats, boxes):
            name = str(name_for_index(cat) if isinstance(cat, int) else cat).lower()
            if name not in wanted:
                continue
            leaf = name
            if counts[leaf] + (existing_w if leaf == "watch" else existing_b) >= (
                min(400, limit) if leaf == "watch" else min(200, limit)
            ):
                continue
            dest = wanted[leaf] / f"fpdet_{seen}_{counts[leaf]}.jpg"
            if _save_crop(image, list(bbox), dest):
                counts[leaf] += 1
        if seen % 250 == 0:
            print(f"  fp scanned {seen}, extra {counts}", flush=True)
    print(f"Fashionpedia extra: {counts} (scanned {seen})", flush=True)
    return counts


def split_pool(seed: int = 23) -> dict[str, dict[str, int]]:
    rng = random.Random(seed)
    report: dict[str, dict[str, int]] = {"train": {}, "val": {}, "test": {}}
    for leaf in ("watch", "belt", "bag", "trousers"):
        files = [
            p
            for p in (OUT / "pool" / leaf).glob("*")
            if p.is_file() and p.suffix.lower() in EXTS
        ]
        files.sort(key=lambda p: p.name)
        rng.shuffle(files)
        n = len(files)
        n_test = max(16, int(n * 0.12)) if n >= 80 else max(4, n // 6)
        n_val = max(16, int(n * 0.12)) if n >= 80 else max(4, n // 6)
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
    ap.add_argument("--limit", type=int, default=700)
    ap.add_argument("--scan", type=int, default=4000)
    ap.add_argument("--skip-hf", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    print("local:", copy_local(args.limit), flush=True)
    if not args.skip_hf:
        try:
            print("myntra:", from_fashion_products(args.limit, args.scan), flush=True)
        except Exception as exc:  # noqa: BLE001
            print("myntra failed:", exc, flush=True)
        try:
            print("fashionpedia:", from_fashionpedia(args.limit, min(args.scan, 1500)), flush=True)
        except Exception as exc:  # noqa: BLE001
            print("fashionpedia failed:", exc, flush=True)
    print("splits:", split_pool(), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
