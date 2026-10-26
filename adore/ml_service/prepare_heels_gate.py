"""Build heels vs other folders from open images.

Positives (heels):
  * local footwear/heels
  * Hugging Face fashion-product-images Heels
    https://huggingface.co/datasets/ashraq/fashion-product-images-small

Hard negatives (the live mistakes are dress and flats):
  * one-piece dresses
  * flats, sneakers
  * shirts, t-shirts, jackets
  * hats, bags, trousers

    .venv\\Scripts\\python.exe prepare_heels_gate.py
"""

from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path

from PIL import Image

LOCAL = Path(r"D:\fyp project\dataset")
OUT = LOCAL / "heels_gate"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
HEELS_ARTICLES = {"heels"}
OTHER_ARTICLES = {
    "shirts",
    "tshirts",
    "jackets",
    "blazers",
    "flats",
    "casual shoes",
    "sports shoes",
    "formal shoes",
    "dresses",
    "dress",
    "gowns",
    "caps",
    "hats",
    "headgear",
    "handbags",
    "jeans",
    "trousers",
    "skirts",
}
FP_TO_LEAF = {
    "dress": "other",
    "shirt, blouse": "other",
    "top, t-shirt, sweatshirt": "other",
    "jacket": "other",
    "coat": "other",
    "hat": "other",
    "pants": "other",
    "skirt": "other",
    "bag, wallet": "other",
}


def _copy_folder(src: Path, dest_dir: Path, prefix: str, limit: int, seed: int = 37) -> int:
    if not src.is_dir():
        return 0
    dest_dir.mkdir(parents=True, exist_ok=True)
    files = [p for p in src.rglob("*") if p.is_file() and p.suffix.lower() in EXTS]
    rng = random.Random(seed)
    rng.shuffle(files)
    n = 0
    for path in files:
        if n >= limit:
            break
        dest = dest_dir / f"{prefix}_{n:05d}{path.suffix.lower()}"
        if not dest.exists():
            shutil.copy2(path, dest)
        n += 1
    return n


def copy_existing(limit: int) -> dict[str, int]:
    heels = _copy_folder(
        LOCAL / "train" / "train" / "footwear" / "heels",
        OUT / "pool" / "heels",
        "local_heels",
        limit,
    )
    other = 0
    other_sources = [
        (LOCAL / "train" / "train" / "upperwear" / "shirt", "shirt", limit),
        (LOCAL / "train" / "train" / "upperwear" / "tshirt", "tshirt", limit // 4),
        (LOCAL / "train" / "train" / "footwear" / "flats", "flats", limit),
        (LOCAL / "train" / "train" / "one-piece" / "dress", "dress", limit),
        (LOCAL / "train" / "train" / "footwear" / "sneakers", "sneakers", max(120, limit // 4)),
        (LOCAL / "train" / "train" / "upperwear" / "jacket", "jacket", max(80, limit // 6)),
        (LOCAL / "train" / "train" / "accessories" / "hat", "hat", limit // 4),
        (LOCAL / "watch_gate" / "pool" / "bag", "bag", limit // 5),
        (LOCAL / "trousers_gate" / "pool" / "trousers", "trousers", limit // 5),
    ]
    for src, prefix, cap in other_sources:
        other += _copy_folder(src, OUT / "pool" / "other", prefix, cap)
    return {"heels": heels, "other": other}


def from_fashion_products(limit: int, scan_limit: int) -> dict[str, int]:
    dests = {"heels": OUT / "pool" / "heels", "other": OUT / "pool" / "other"}
    for folder in dests.values():
        folder.mkdir(parents=True, exist_ok=True)
    try:
        from datasets import load_dataset
    except ImportError:
        print("datasets missing; skip HF fashion-product-images")
        return {"heels": 0, "other": 0}
    print("Streaming heels vs other from fashion-product-images-small…", flush=True)
    try:
        ds = load_dataset(
            "ashraq/fashion-product-images-small",
            split="train",
            streaming=True,
        )
    except Exception as exc:  # noqa: BLE001
        print("HF load failed:", exc, flush=True)
        return {"heels": 0, "other": 0}
    saved = {"heels": 0, "other": 0}
    seen = 0
    for row in ds:
        seen += 1
        if seen > scan_limit:
            break
        if saved["heels"] >= limit and saved["other"] >= limit:
            break
        article = str(row.get("articleType") or "").lower().strip()
        if article in HEELS_ARTICLES:
            leaf = "heels"
        elif article in OTHER_ARTICLES:
            leaf = "other"
        else:
            continue
        if saved[leaf] >= limit:
            continue
        image = row.get("image")
        if image is None:
            continue
        dest = dests[leaf] / f"hf_{leaf}_{seen}_{saved[leaf]:05d}.jpg"
        if dest.exists():
            continue
        try:
            image.convert("RGB").save(dest, format="JPEG", quality=90)
            saved[leaf] += 1
        except Exception:  # noqa: BLE001
            continue
        if seen % 1500 == 0:
            print(f"  scanned {seen}, extra {saved}", flush=True)
    print(f"hf extra {saved} (scanned {seen})", flush=True)
    return saved


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
    counts = {"heels": 0, "other": 0}
    dests = {leaf: OUT / "pool" / leaf for leaf in counts}
    for folder in dests.values():
        folder.mkdir(parents=True, exist_ok=True)
    cap = {"heels": 0, "other": min(400, limit)}
    try:
        from datasets import load_dataset
        from app.fashionpedia_map import name_for_index
    except Exception as exc:  # noqa: BLE001
        print("Fashionpedia harvest skipped:", exc, flush=True)
        return counts
    print("Streaming Fashionpedia val for shirt/hat negatives…", flush=True)
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
        if all(counts[leaf] >= cap[leaf] for leaf in counts if cap[leaf] > 0):
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
            leaf = FP_TO_LEAF.get(name)
            if leaf is None:
                continue
            if counts[leaf] >= cap[leaf]:
                continue
            dest = dests[leaf] / f"fpdet_{leaf}_{seen}_{counts[leaf]}.jpg"
            if _save_crop(image, list(bbox), dest):
                counts[leaf] += 1
        if seen % 250 == 0:
            print(f"  fp scanned {seen}, extra {counts}", flush=True)
    print(f"Fashionpedia extra: {counts} (scanned {seen})", flush=True)
    return counts


def split_pool(seed: int = 53) -> dict[str, dict[str, int]]:
    rng = random.Random(seed)
    report: dict[str, dict[str, int]] = {"train": {}, "val": {}, "test": {}}
    for leaf in ("heels", "other"):
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
    ap.add_argument("--limit", type=int, default=600)
    ap.add_argument("--scan", type=int, default=15000)
    ap.add_argument("--skip-hf", action="store_true")
    ap.add_argument("--skip-fashionpedia", action="store_true")
    args = ap.parse_args()
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    print("local:", copy_existing(args.limit), flush=True)
    if not args.skip_hf:
        try:
            print("hf:", from_fashion_products(min(args.limit, 500), args.scan), flush=True)
        except Exception as exc:  # noqa: BLE001
            print("hf failed:", exc, flush=True)
    if not args.skip_fashionpedia:
        try:
            print(
                "fashionpedia:",
                from_fashionpedia(args.limit, min(args.scan, 2000)),
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001
            print("fashionpedia failed:", exc, flush=True)
    print("splits:", split_pool(), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
