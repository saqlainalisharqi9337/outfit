"""Build trousers vs dress vs shirt folders from open images.

Trousers:
  * local bottomwear/pants
  * Hugging Face fashion-product-images Trousers / Jeans / Track Pants
    https://huggingface.co/datasets/ashraq/fashion-product-images-small
  * Fashionpedia pants crops (https://fashionpedia.github.io )

Hard negatives (the live mistakes):
  * local one-piece/dress + HF Dresses + Fashionpedia dress
  * local upperwear/shirt + HF Shirts/Tshirts + Fashionpedia shirt/top

    .venv\\Scripts\\python.exe prepare_trousers_gate.py
"""

from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path

from PIL import Image

LOCAL = Path(r"D:\fyp project\dataset")
OUT = LOCAL / "trousers_gate"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
TROUSERS_ARTICLES = {"trousers", "jeans", "track pants", "lounge pants"}
DRESS_ARTICLES = {"dresses", "dress"}
SHIRT_ARTICLES = {"shirts", "tshirts", "tops"}
FP_TO_LEAF = {
    "pants": "trousers",
    "dress": "dress",
    "shirt, blouse": "shirt",
    "top, t-shirt, sweatshirt": "shirt",
}


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


def copy_existing(limit: int) -> dict[str, int]:
    counts = {
        "trousers": _copy_folder(
            LOCAL / "train" / "train" / "bottomwear" / "pants",
            OUT / "pool" / "trousers",
            "local_pants",
            limit,
        ),
        "dress": _copy_folder(
            LOCAL / "train" / "train" / "one-piece" / "dress",
            OUT / "pool" / "dress",
            "local_dress",
            limit,
        ),
        "shirt": _copy_folder(
            LOCAL / "train" / "train" / "upperwear" / "shirt",
            OUT / "pool" / "shirt",
            "local_shirt",
            limit,
        ),
    }
    counts["shirt"] += _copy_folder(
        LOCAL / "train" / "train" / "upperwear" / "tshirt",
        OUT / "pool" / "shirt",
        "local_tshirt",
        max(80, limit // 3),
    )
    return counts


def from_fashion_products(limit: int, scan_limit: int) -> dict[str, int]:
    dests = {
        "trousers": OUT / "pool" / "trousers",
        "dress": OUT / "pool" / "dress",
        "shirt": OUT / "pool" / "shirt",
    }
    for folder in dests.values():
        folder.mkdir(parents=True, exist_ok=True)
    existing = {leaf: len(list(folder.glob("*"))) for leaf, folder in dests.items()}
    if all(existing[leaf] >= limit for leaf in dests):
        print(f"hf skip, already {existing}")
        return {"trousers": 0, "dress": 0, "shirt": 0}
    try:
        from datasets import load_dataset
    except ImportError:
        print("datasets missing; skip HF fashion-product-images")
        return {"trousers": 0, "dress": 0, "shirt": 0}
    print("Streaming trousers/dress/shirt from fashion-product-images-small…", flush=True)
    try:
        ds = load_dataset(
            "ashraq/fashion-product-images-small",
            split="train",
            streaming=True,
        )
    except Exception as exc:  # noqa: BLE001
        print("HF load failed:", exc, flush=True)
        return {"trousers": 0, "dress": 0, "shirt": 0}
    saved = {"trousers": 0, "dress": 0, "shirt": 0}
    seen = 0
    for row in ds:
        seen += 1
        if seen > scan_limit:
            break
        if all(existing[leaf] + saved[leaf] >= limit for leaf in dests):
            break
        article = str(row.get("articleType") or "").lower().strip()
        if article in TROUSERS_ARTICLES:
            leaf = "trousers"
        elif article in DRESS_ARTICLES:
            leaf = "dress"
        elif article in SHIRT_ARTICLES:
            leaf = "shirt"
        else:
            continue
        if existing[leaf] + saved[leaf] >= limit:
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
        if seen % 800 == 0:
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
    counts = {"trousers": 0, "dress": 0, "shirt": 0}
    dests = {leaf: OUT / "pool" / leaf for leaf in counts}
    for folder in dests.values():
        folder.mkdir(parents=True, exist_ok=True)
    existing = {
        leaf: len(list(folder.glob("fpdet_*"))) for leaf, folder in dests.items()
    }
    cap = {leaf: min(400, limit) for leaf in counts}
    if all(existing[leaf] >= cap[leaf] for leaf in counts):
        print("Fashionpedia trousers/dress/shirt skip, already harvested")
        return counts
    try:
        from datasets import load_dataset
        from app.fashionpedia_map import name_for_index
    except Exception as exc:  # noqa: BLE001
        print("Fashionpedia harvest skipped:", exc, flush=True)
        return counts
    print("Streaming Fashionpedia val for pants/dress/shirt…", flush=True)
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
        if all(counts[leaf] + existing[leaf] >= cap[leaf] for leaf in counts):
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
            if counts[leaf] + existing[leaf] >= cap[leaf]:
                continue
            dest = dests[leaf] / f"fpdet_{seen}_{counts[leaf]}.jpg"
            if _save_crop(image, list(bbox), dest):
                counts[leaf] += 1
        if seen % 250 == 0:
            print(f"  fp scanned {seen}, extra {counts}", flush=True)
    print(f"Fashionpedia extra: {counts} (scanned {seen})", flush=True)
    return counts


def split_pool(seed: int = 41) -> dict[str, dict[str, int]]:
    rng = random.Random(seed)
    report: dict[str, dict[str, int]] = {"train": {}, "val": {}, "test": {}}
    for leaf in ("trousers", "dress", "shirt"):
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
    ap.add_argument("--limit", type=int, default=500)
    ap.add_argument("--scan", type=int, default=8000)
    ap.add_argument("--skip-hf", action="store_true")
    ap.add_argument("--skip-fashionpedia", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    print("local:", copy_existing(args.limit), flush=True)
    if not args.skip_hf:
        try:
            print("hf:", from_fashion_products(args.limit, args.scan), flush=True)
        except Exception as exc:  # noqa: BLE001
            print("hf failed:", exc, flush=True)
    if not args.skip_fashionpedia:
        try:
            print(
                "fashionpedia:",
                from_fashionpedia(args.limit, min(args.scan, 1500)),
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001
            print("fashionpedia failed:", exc, flush=True)
    print("splits:", split_pool(), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
