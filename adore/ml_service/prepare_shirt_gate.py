"""Build a fresh shirt vs other dataset from open images.

Positives (shirt):
  * local upperwear/shirt and tshirt
  * Hugging Face fashion-product-images Shirts / Tshirts / Tops
    https://huggingface.co/datasets/ashraq/fashion-product-images-small
  * Fashionpedia shirt/blouse and top crops (https://fashionpedia.github.io )

Negatives (other — the live collisions, plus classes we must not steal):
  * dupatta, hat, dress
  * bag, trousers, skirt, watch

    .venv\\Scripts\\python.exe prepare_shirt_gate.py
"""

from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path

from PIL import Image

LOCAL = Path(r"D:\fyp project\dataset")
OUT = LOCAL / "shirt_detector"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
SHIRT_ARTICLES = {"shirts", "tshirts", "tops"}
OTHER_ARTICLES = {
    "dresses",
    "dress",
    "dupatta",
    "stoles",
    "stole",
    "caps",
    "hats",
    "headgear",
    "jeans",
    "trousers",
    "track pants",
    "skirts",
    "handbags",
    "watches",
    "belts",
}
FP_TO_LEAF = {
    "shirt, blouse": "shirt",
    "top, t-shirt, sweatshirt": "shirt",
    "hat": "other",
    "scarf": "other",
    "dress": "other",
    "pants": "other",
    "skirt": "other",
    "bag, wallet": "other",
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
    shirt = _copy_folder(
        LOCAL / "train" / "train" / "upperwear" / "shirt",
        OUT / "pool" / "shirt",
        "local_shirt",
        limit,
    )
    shirt += _copy_folder(
        LOCAL / "train" / "train" / "upperwear" / "tshirt",
        OUT / "pool" / "shirt",
        "local_tshirt",
        max(120, limit // 2),
    )
    shirt += _copy_folder(
        LOCAL / "shirt_gate" / "pool" / "shirt",
        OUT / "pool" / "shirt",
        "prev_shirt",
        limit,
    )
    other = 0
    other_sources = [
        (LOCAL / "dupatta_gate" / "pool" / "dupatta", "dupatta", limit // 3),
        (LOCAL / "accessories_open" / "pool" / "dupatta", "open_dupatta", limit // 4),
        (LOCAL / "train" / "train" / "accessories" / "hat", "hat", limit // 3),
        (LOCAL / "hat_gate" / "pool" / "hat", "hat_gate", limit // 4),
        (LOCAL / "train" / "train" / "one-piece" / "dress", "dress", limit // 3),
        (LOCAL / "shirt_gate" / "pool" / "dress", "fp_dress", limit // 3),
        (LOCAL / "shirt_gate" / "pool" / "dupatta", "fp_dupatta", limit // 4),
        (LOCAL / "shirt_gate" / "pool" / "hat", "fp_hat", limit // 4),
        (LOCAL / "watch_gate" / "pool" / "bag", "bag", limit // 5),
        (LOCAL / "trousers_gate" / "pool" / "trousers", "trousers", limit // 5),
        (LOCAL / "skirt_gate" / "pool" / "skirt", "skirt", limit // 5),
        (LOCAL / "watch_gate" / "pool" / "watch", "watch", limit // 6),
    ]
    for src, prefix, cap in other_sources:
        other += _copy_folder(src, OUT / "pool" / "other", prefix, cap)
    return {"shirt": shirt, "other": other}


def from_fashion_products(limit: int, scan_limit: int) -> dict[str, int]:
    dests = {"shirt": OUT / "pool" / "shirt", "other": OUT / "pool" / "other"}
    for folder in dests.values():
        folder.mkdir(parents=True, exist_ok=True)
    existing = {leaf: len(list(folder.glob("*"))) for leaf, folder in dests.items()}
    if all(existing[leaf] >= limit for leaf in dests):
        print(f"hf skip, already {existing}")
        return {"shirt": 0, "other": 0}
    try:
        from datasets import load_dataset
    except ImportError:
        print("datasets missing; skip HF fashion-product-images")
        return {"shirt": 0, "other": 0}
    print("Streaming shirts vs other from fashion-product-images-small…", flush=True)
    try:
        ds = load_dataset(
            "ashraq/fashion-product-images-small",
            split="train",
            streaming=True,
        )
    except Exception as exc:  # noqa: BLE001
        print("HF load failed:", exc, flush=True)
        return {"shirt": 0, "other": 0}
    saved = {"shirt": 0, "other": 0}
    seen = 0
    for row in ds:
        seen += 1
        if seen > scan_limit:
            break
        if all(existing[leaf] + saved[leaf] >= limit for leaf in dests):
            break
        article = str(row.get("articleType") or "").lower().strip()
        if article in SHIRT_ARTICLES:
            leaf = "shirt"
        elif article in OTHER_ARTICLES:
            leaf = "other"
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
    counts = {"shirt": 0, "other": 0}
    dests = {leaf: OUT / "pool" / leaf for leaf in counts}
    for folder in dests.values():
        folder.mkdir(parents=True, exist_ok=True)
    existing = {
        leaf: len(list(folder.glob("fpdet_*"))) for leaf, folder in dests.items()
    }
    cap = {"shirt": min(500, limit), "other": min(400, limit)}
    if all(existing[leaf] >= cap[leaf] for leaf in counts):
        print("Fashionpedia shirt detector skip, already harvested")
        return counts
    try:
        from datasets import load_dataset
        from app.fashionpedia_map import name_for_index
    except Exception as exc:  # noqa: BLE001
        print("Fashionpedia harvest skipped:", exc, flush=True)
        return counts
    print("Streaming Fashionpedia val for shirts vs other…", flush=True)
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


def split_pool(seed: int = 61) -> dict[str, dict[str, int]]:
    rng = random.Random(seed)
    report: dict[str, dict[str, int]] = {"train": {}, "val": {}, "test": {}}
    for leaf in ("shirt", "other"):
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
    ap.add_argument("--scan", type=int, default=9000)
    ap.add_argument("--skip-hf", action="store_true")
    ap.add_argument("--skip-fashionpedia", action="store_true")
    args = ap.parse_args()
    if OUT.exists():
        shutil.rmtree(OUT)
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
                from_fashionpedia(args.limit, min(args.scan, 1800)),
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001
            print("fashionpedia failed:", exc, flush=True)
    print("splits:", split_pool(), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
