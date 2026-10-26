"""Build a fresh jacket vs other dataset from open images.

Positives (jacket):
  * local upperwear/jacket (shuffled, including vests and zip fleeces)
  * Hugging Face fashion-product-images Jackets / Blazers / Rain Jacket
    https://huggingface.co/datasets/ashraq/fashion-product-images-small
  * Fashionpedia jacket, coat, and vest crops (https://fashionpedia.github.io )

Negatives (other — shirts/bags the live mistakes, plus classes we must not steal):
  * shirts, t-shirts, hats, bags, trousers, skirts, dupattas

    .venv\\Scripts\\python.exe prepare_jacket_gate.py
"""

from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path

from PIL import Image

LOCAL = Path(r"D:\fyp project\dataset")
OUT = LOCAL / "jacket_gate"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
JACKET_ARTICLES = {
    "jackets",
    "blazers",
    "rain jacket",
    "nehru jackets",
    "waistcoat",
}
OTHER_ARTICLES = {
    "shirts",
    "tshirts",
    "tops",
    "caps",
    "hats",
    "headgear",
    "jeans",
    "trousers",
    "track pants",
    "skirts",
    "handbags",
    "clutches",
    "backpacks",
    "dupatta",
    "stoles",
    "dresses",
}
FP_TO_LEAF = {
    "jacket": "jacket",
    "coat": "jacket",
    "vest": "jacket",
    "cape": "jacket",
    "shirt, blouse": "other",
    "top, t-shirt, sweatshirt": "other",
    "hat": "other",
    "pants": "other",
    "skirt": "other",
    "bag, wallet": "other",
    "scarf": "other",
    "dress": "other",
}
HARD_JACKETS = (
    "10.png",
    "103.png",
    "00208c77-ee58-4b63-bc1a-b9b3aa4f1be0.jpg",
)


def _copy_folder(src: Path, dest_dir: Path, prefix: str, limit: int, seed: int = 19) -> int:
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


def _copy_named(src: Path, dest_dir: Path, names: tuple[str, ...], prefix: str) -> int:
    if not src.is_dir():
        return 0
    dest_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for name in names:
        path = src / name
        if not path.is_file():
            matches = list(src.glob(name.split(".")[0] + ".*"))
            path = matches[0] if matches else path
        if not path.is_file():
            continue
        dest = dest_dir / f"{prefix}_{n:05d}{path.suffix.lower()}"
        shutil.copy2(path, dest)
        n += 1
    return n


def copy_existing(limit: int) -> dict[str, int]:
    dest = OUT / "pool" / "jacket"
    jacket = _copy_folder(
        LOCAL / "train" / "train" / "upperwear" / "jacket",
        dest,
        "local_jacket",
        limit,
    )
    jacket += _copy_named(
        LOCAL / "train" / "train" / "upperwear" / "jacket",
        dest,
        HARD_JACKETS,
        "hard_jacket",
    )
    other = 0
    other_sources = [
        (LOCAL / "train" / "train" / "upperwear" / "shirt", "local_shirt", limit),
        (LOCAL / "train" / "train" / "upperwear" / "tshirt", "local_tshirt", max(160, limit // 2)),
        (LOCAL / "train" / "train" / "accessories" / "hat", "hat", limit // 3),
        (LOCAL / "hat_gate" / "pool" / "hat", "hat_gate", limit // 4),
        (LOCAL / "watch_gate" / "pool" / "bag", "bag", max(160, limit // 4)),
        (LOCAL / "watch_gate" / "test" / "bag", "bag_test", 80),
        (LOCAL / "trousers_gate" / "pool" / "trousers", "trousers", limit // 5),
        (LOCAL / "skirt_gate" / "pool" / "skirt", "skirt", limit // 5),
        (LOCAL / "dupatta_gate" / "pool" / "dupatta", "dupatta", limit // 4),
        (LOCAL / "train" / "train" / "one-piece" / "dress", "dress", limit // 5),
    ]
    for src, prefix, cap in other_sources:
        other += _copy_folder(src, OUT / "pool" / "other", prefix, cap)
    return {"jacket": jacket, "other": other}


def from_fashion_products(limit: int, scan_limit: int) -> dict[str, int]:
    dests = {"jacket": OUT / "pool" / "jacket", "other": OUT / "pool" / "other"}
    for folder in dests.values():
        folder.mkdir(parents=True, exist_ok=True)
    try:
        from datasets import load_dataset
    except ImportError:
        print("datasets missing; skip HF fashion-product-images")
        return {"jacket": 0, "other": 0}
    print("Streaming jackets vs other from fashion-product-images-small…", flush=True)
    try:
        ds = load_dataset(
            "ashraq/fashion-product-images-small",
            split="train",
            streaming=True,
        )
    except Exception as exc:  # noqa: BLE001
        print("HF load failed:", exc, flush=True)
        return {"jacket": 0, "other": 0}
    saved = {"jacket": 0, "other": 0}
    seen = 0
    for row in ds:
        seen += 1
        if seen > scan_limit:
            break
        if saved["jacket"] >= limit and saved["other"] >= limit:
            break
        article = str(row.get("articleType") or "").lower().strip()
        if article in JACKET_ARTICLES:
            leaf = "jacket"
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


def from_fashionpedia(limit: int, scan_limit: int, split: str) -> dict[str, int]:
    counts = {"jacket": 0, "other": 0}
    dests = {leaf: OUT / "pool" / leaf for leaf in counts}
    for folder in dests.values():
        folder.mkdir(parents=True, exist_ok=True)
    cap = {"jacket": min(500, limit), "other": min(350, limit)}
    try:
        from datasets import load_dataset
        from app.fashionpedia_map import name_for_index
    except Exception as exc:  # noqa: BLE001
        print("Fashionpedia harvest skipped:", exc, flush=True)
        return counts
    print(f"Streaming Fashionpedia {split} for jacket vs other…", flush=True)
    try:
        ds = load_dataset("detection-datasets/fashionpedia", split=split, streaming=True)
    except Exception as exc:  # noqa: BLE001
        print("Fashionpedia load failed:", exc, flush=True)
        return counts
    seen = 0
    for row in ds:
        seen += 1
        if seen > scan_limit:
            break
        if all(counts[leaf] >= cap[leaf] for leaf in counts):
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
            dest = dests[leaf] / f"fp_{split}_{leaf}_{seen}_{counts[leaf]}.jpg"
            if _save_crop(image, list(bbox), dest):
                counts[leaf] += 1
        if seen % 250 == 0:
            print(f"  fp {split} scanned {seen}, extra {counts}", flush=True)
    print(f"Fashionpedia {split} extra: {counts} (scanned {seen})", flush=True)
    return counts


def split_pool(seed: int = 83) -> dict[str, dict[str, int]]:
    rng = random.Random(seed)
    report: dict[str, dict[str, int]] = {"train": {}, "val": {}, "test": {}}
    for leaf in ("jacket", "other"):
        files = [
            p
            for p in (OUT / "pool" / leaf).glob("*")
            if p.is_file() and p.suffix.lower() in EXTS
        ]
        files.sort(key=lambda p: p.name)
        hard = [p for p in files if p.name.startswith("hard_jacket_")]
        rest = [p for p in files if not p.name.startswith("hard_jacket_")]
        rng.shuffle(rest)
        n = len(rest)
        n_test = max(16, int(n * 0.10)) if n >= 80 else max(4, n // 6)
        n_val = max(16, int(n * 0.10)) if n >= 80 else max(4, n // 6)
        test, val, train = rest[:n_test], rest[n_test : n_test + n_val], rest[n_test + n_val :]
        train = hard + train
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
    ap.add_argument("--limit", type=int, default=800)
    ap.add_argument("--scan", type=int, default=25000)
    ap.add_argument("--skip-hf", action="store_true")
    ap.add_argument("--skip-fashionpedia", action="store_true")
    args = ap.parse_args()
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    print("local:", copy_existing(args.limit), flush=True)
    if not args.skip_hf:
        try:
            print("hf:", from_fashion_products(min(args.limit, 600), args.scan), flush=True)
        except Exception as exc:  # noqa: BLE001
            print("hf failed:", exc, flush=True)
    if not args.skip_fashionpedia:
        for split, scan in (("val", 2000), ("train", 2500)):
            try:
                print(
                    f"fashionpedia {split}:",
                    from_fashionpedia(args.limit, scan, split),
                    flush=True,
                )
            except Exception as exc:  # noqa: BLE001
                print(f"fashionpedia {split} failed:", exc, flush=True)
    print("splits:", split_pool(), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
