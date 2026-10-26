"""Build watch vs bag vs trousers folders from open images.

Watches:
  * already harvested Fashionpedia + fashion-product-images watches
  * extra Hugging Face fashion-product-images Watches
    https://huggingface.co/datasets/ashraq/fashion-product-images-small

Hard negatives:
  * local bags
  * local trousers

    .venv\\Scripts\\python.exe prepare_watch_gate.py
"""

from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path

from PIL import Image

LOCAL = Path(r"D:\fyp project\dataset")
PREV = LOCAL / "watch_belt_gate"
OUT = LOCAL / "watch_gate"
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


def copy_existing(limit: int) -> dict[str, int]:
    counts = {
        "watch_prev": _copy_folder(PREV / "pool" / "watch", OUT / "pool" / "watch", "prev", limit),
        "bag": _copy_folder(
            LOCAL / "train" / "train" / "accessories" / "bag",
            OUT / "pool" / "bag",
            "local_bag",
            limit,
        ),
        "trousers": _copy_folder(
            LOCAL / "train" / "train" / "bottomwear" / "pants",
            OUT / "pool" / "trousers",
            "local_pants",
            limit,
        ),
    }
    return counts


def from_fashion_products(limit: int, scan_limit: int) -> int:
    dest = OUT / "pool" / "watch"
    dest.mkdir(parents=True, exist_ok=True)
    existing = len(list(dest.glob("*")))
    if existing >= limit:
        print(f"watches skip extra HF, already {existing}")
        return 0
    try:
        from datasets import load_dataset
    except ImportError:
        print("datasets missing; skip extra watches")
        return 0
    print("Streaming extra Watches from fashion-product-images-small…", flush=True)
    try:
        ds = load_dataset(
            "ashraq/fashion-product-images-small",
            split="train",
            streaming=True,
        )
    except Exception as exc:  # noqa: BLE001
        print("HF load failed:", exc, flush=True)
        return 0
    saved = 0
    seen = 0
    for row in ds:
        seen += 1
        if seen > scan_limit or existing + saved >= limit:
            break
        article = str(row.get("articleType") or "").lower()
        if article != "watches":
            continue
        image = row.get("image")
        if image is None:
            continue
        dest_path = dest / f"hfwatch_{seen}_{saved:05d}.jpg"
        if dest_path.exists():
            continue
        try:
            image.convert("RGB").save(dest_path, format="JPEG", quality=90)
            saved += 1
        except Exception:  # noqa: BLE001
            continue
        if seen % 800 == 0:
            print(f"  scanned {seen}, extra watches {saved}", flush=True)
    print(f"extra watches {saved} (scanned {seen})", flush=True)
    return saved


def split_pool(seed: int = 29) -> dict[str, dict[str, int]]:
    rng = random.Random(seed)
    report: dict[str, dict[str, int]] = {"train": {}, "val": {}, "test": {}}
    for leaf in ("watch", "bag", "trousers"):
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
    ap.add_argument("--scan", type=int, default=10000)
    ap.add_argument("--skip-hf", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    print("local:", copy_existing(args.limit), flush=True)
    if not args.skip_hf:
        try:
            print("hf:", from_fashion_products(args.limit, args.scan), flush=True)
        except Exception as exc:  # noqa: BLE001
            print("hf failed:", exc, flush=True)
    print("splits:", split_pool(), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
