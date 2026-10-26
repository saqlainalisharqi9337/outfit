"""Build an 8-class accessory crop dataset from public sources.

Sources (no commercial scraping):
  * Fashionpedia on Hugging Face — https://huggingface.co/datasets/detection-datasets/fashionpedia
    (Jia et al., CVPR 2020; same ontology as https://fashionpedia.github.io )
  * Existing Adore bag/hat folders
  * Wikimedia Commons CC images for hijab, dupatta, jewellery

DeepFashion2 is intentionally **not** used: its 13 classes are garments only
(https://github.com/switchablenorms/DeepFashion2). Training on it is what
mapped bags to skirts and caps to dresses.

    .venv\\Scripts\\python.exe prepare_accessory_dataset.py
"""

from __future__ import annotations

import argparse
import hashlib
import random
import shutil
from collections import defaultdict
from pathlib import Path

from PIL import Image

from app.fashionpedia_map import ACCESSORY_LEAVES, TRAIN_CROP_FROM_FASHIONPEDIA
from download_wikimedia_weak_classes import UA, file_info, search_files

ROOT = Path(__file__).resolve().parent
DEFAULT_OUT = Path(r"D:\fyp project\dataset") / "accessories_open"
LOCAL_DATASET = Path(r"D:\fyp project\dataset")
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

WIKI_QUERIES: list[tuple[str, str]] = [
    ("hijab", "hijab"),
    ("khimar", "hijab"),
    ("dupatta", "dupatta"),
    ("necklace jewellery", "jewelry"),
    ("earrings jewellery", "jewelry"),
    ("bracelet jewellery", "jewelry"),
    ("sunglasses", "sunglasses"),
    ("leather belt fashion", "belt"),
    ("silk scarf", "scarf"),
    ("baseball cap", "hat"),
]


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
    if x2 - x1 < 24 or y2 - y1 < 24:
        return False
    crop = image.crop((int(x1), int(y1), int(x2), int(y2))).convert("RGB")
    dest.parent.mkdir(parents=True, exist_ok=True)
    crop.save(dest, format="JPEG", quality=90)
    return True


def _digest(path: Path) -> str:
    return hashlib.md5(path.read_bytes()[:32768]).hexdigest()


def copy_local(out: Path, max_per_class: int) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    mapping = {
        ("accessories", "bag"): "bag",
        ("accessories", "hat"): "hat",
        ("accessories", "scarf"): "scarf",
        ("accessories", "belt"): "belt",
        ("accessories", "dupatta"): "dupatta",
        ("accessories", "hijab"): "hijab",
        ("accessories", "jewelry"): "jewelry",
        ("accessories", "jewellery"): "jewelry",
        ("accessories", "sunglasses"): "sunglasses",
        ("accessories", "glasses"): "sunglasses",
    }
    for split in ("train", "val", "test"):
        base = LOCAL_DATASET / split / split
        if not base.is_dir():
            continue
        for (family, leaf), label in mapping.items():
            folder = base / family / leaf
            if not folder.is_dir():
                continue
            for src in folder.iterdir():
                if counts[label] >= max_per_class:
                    break
                if not src.is_file() or src.suffix.lower() not in EXTS:
                    continue
                dest = out / "pool" / label / f"local_{src.name}"
                dest.parent.mkdir(parents=True, exist_ok=True)
                if dest.exists():
                    counts[label] += 1
                    continue
                shutil.copy2(src, dest)
                counts[label] += 1
    return dict(counts)


def from_fashionpedia(out: Path, max_per_class: int, scan_limit: int) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    try:
        from datasets import load_dataset
    except ImportError:
        print("datasets package missing; skip Fashionpedia download")
        return {}
    print("Streaming Fashionpedia from Hugging Face…", flush=True)
    splits = ("val", "train")
    seen = 0
    for split_name in splits:
        if all(counts.get(leaf, 0) >= max_per_class for leaf in TRAIN_CROP_FROM_FASHIONPEDIA.values()):
            break
        try:
            ds = load_dataset(
                "detection-datasets/fashionpedia",
                split=split_name,
                streaming=True,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  could not open {split_name}: {exc}", flush=True)
            continue
        for row in ds:
            seen += 1
            if seen > scan_limit:
                break
            if all(
                counts.get(leaf, 0) >= max_per_class
                for leaf in TRAIN_CROP_FROM_FASHIONPEDIA.values()
            ):
                break
            objects = row.get("objects") or {}
            categories = objects.get("category") or []
            boxes = objects.get("bbox") or []
            image = row.get("image")
            if image is None or not categories:
                continue
            image = image.convert("RGB")
            for cat, bbox in zip(categories, boxes):
                if isinstance(cat, int):
                    from app.fashionpedia_map import name_for_index

                    cat = name_for_index(cat)
                leaf = TRAIN_CROP_FROM_FASHIONPEDIA.get(str(cat))
                if leaf is None or counts[leaf] >= max_per_class:
                    continue
                dest = out / "pool" / leaf / f"fp_{row.get('image_id', seen)}_{counts[leaf]}.jpg"
                if _save_crop(image, list(bbox), dest):
                    counts[leaf] += 1
            if seen % 200 == 0:
                print(f"  scanned {seen} images, crops={dict(counts)}", flush=True)
        print(f"  split {split_name} done, crops={dict(counts)}", flush=True)
    print(f"Fashionpedia crops: {dict(counts)} (scanned {seen})", flush=True)
    return dict(counts)


def seed_dupatta_from_scarf(out: Path, limit: int = 80) -> int:
    """Dupatta is not a Fashionpedia class; use draped-scarf crops as a start."""
    scarf = list((out / "pool" / "scarf").glob("*"))
    dest_dir = out / "pool" / "dupatta"
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for src in scarf[:limit]:
        dest = dest_dir / f"drape_{src.name}"
        if dest.exists():
            copied += 1
            continue
        shutil.copy2(src, dest)
        copied += 1
    return copied


def from_wikimedia(out: Path, per_query: int) -> dict[str, int]:
    import time
    import urllib.request

    counts: dict[str, int] = defaultdict(int)
    for query, leaf in WIKI_QUERIES:
        try:
            titles = search_files(query, limit=per_query)
            infos = file_info(titles)
        except Exception as exc:  # noqa: BLE001
            print(f"  wiki query failed {query}: {exc}")
            continue
        for info in infos:
            url = info.get("url")
            if not url:
                continue
            dest = out / "pool" / leaf / f"wiki_{counts[leaf]}_{leaf}.jpg"
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                counts[leaf] += 1
                continue
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    raw = resp.read()
                if len(raw) < 5000:
                    continue
                dest.write_bytes(raw)
                counts[leaf] += 1
                time.sleep(0.12)
            except Exception as exc:  # noqa: BLE001
                print(f"  wiki skip {query}: {exc}")
        print(f"  wikimedia {leaf}/{query}: {counts[leaf]}")
        time.sleep(0.25)
    return dict(counts)


def split_pool(out: Path, seed: int = 7) -> dict[str, dict[str, int]]:
    rng = random.Random(seed)
    report: dict[str, dict[str, int]] = {"train": {}, "val": {}, "test": {}}
    for leaf in ACCESSORY_LEAVES:
        files = [
            p
            for p in (out / "pool" / leaf).glob("*")
            if p.is_file() and p.suffix.lower() in EXTS
        ]
        files.sort(key=lambda p: p.name)
        rng.shuffle(files)
        n = len(files)
        n_test = max(8, int(n * 0.12)) if n >= 40 else max(2, n // 5)
        n_val = max(8, int(n * 0.12)) if n >= 40 else max(2, n // 5)
        test, val, train = files[:n_test], files[n_test : n_test + n_val], files[n_test + n_val :]
        for split, group in (("test", test), ("val", val), ("train", train)):
            dest_dir = out / split / leaf
            dest_dir.mkdir(parents=True, exist_ok=True)
            for src in group:
                dest = dest_dir / src.name
                if not dest.exists():
                    shutil.copy2(src, dest)
            report[split][leaf] = len(group)
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-per-class", type=int, default=360)
    ap.add_argument("--scan-limit", type=int, default=12000)
    ap.add_argument("--wiki-per-query", type=int, default=40)
    ap.add_argument("--skip-fashionpedia", action="store_true")
    ap.add_argument("--skip-wiki", action="store_true")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    local = copy_local(args.out, args.max_per_class)
    print("local copies:", local, flush=True)
    if not args.skip_wiki:
        try:
            print("wikimedia:", from_wikimedia(args.out, args.wiki_per_query), flush=True)
        except Exception as exc:  # noqa: BLE001
            print("wikimedia failed:", exc, flush=True)
    if not args.skip_fashionpedia:
        print("fashionpedia:", from_fashionpedia(args.out, args.max_per_class, args.scan_limit), flush=True)
    copied = seed_dupatta_from_scarf(args.out)
    print("dupatta from scarf:", copied, flush=True)
    report = split_pool(args.out)
    print("splits:", report)
    (args.out / "manifest.json").write_text(
        __import__("json").dumps(
            {"local": local, "splits": report, "classes": list(ACCESSORY_LEAVES)},
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
