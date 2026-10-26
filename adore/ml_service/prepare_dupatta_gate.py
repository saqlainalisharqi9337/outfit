"""Build dupatta vs bag vs belt folders from open images.

Dupattas:
  * existing Fashionpedia/Wikimedia dupatta crops in accessories_open
  * Hugging Face fashion-product-images Dupatta and Stoles
    https://huggingface.co/datasets/ashraq/fashion-product-images-small

Hard negatives (the live mistakes):
  * local bags
  * Fashionpedia / open belts

    .venv\\Scripts\\python.exe prepare_dupatta_gate.py
"""

from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path

LOCAL = Path(r"D:\fyp project\dataset")
OPEN = LOCAL / "accessories_open"
OUT = LOCAL / "dupatta_gate"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
DUPATTA_ARTICLES = {"dupatta", "stoles", "stole"}


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
        "dupatta_open": _copy_folder(OPEN / "pool" / "dupatta", OUT / "pool" / "dupatta", "open", limit),
        "bag": _copy_folder(
            LOCAL / "train" / "train" / "accessories" / "bag",
            OUT / "pool" / "bag",
            "local_bag",
            limit,
        ),
        "belt": _copy_folder(OPEN / "pool" / "belt", OUT / "pool" / "belt", "fp_belt", limit),
    }
    for split in ("train", "val", "test"):
        counts["dupatta_open"] += _copy_folder(
            OPEN / split / "dupatta", OUT / "pool" / "dupatta", f"open_{split}", limit
        )
    extra_belts = LOCAL / "watch_belt_gate" / "pool" / "belt"
    counts["belt"] += _copy_folder(extra_belts, OUT / "pool" / "belt", "wb_belt", limit)
    return counts


def from_fashion_products(limit: int, scan_limit: int) -> int:
    dest = OUT / "pool" / "dupatta"
    dest.mkdir(parents=True, exist_ok=True)
    existing = len(list(dest.glob("*")))
    if existing >= limit:
        print(f"dupatta skip extra HF, already {existing}")
        return 0
    try:
        from datasets import load_dataset
    except ImportError:
        print("datasets missing; skip extra dupattas")
        return 0
    print("Streaming Dupatta/Stoles from fashion-product-images-small…", flush=True)
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
        article = str(row.get("articleType") or "").lower().strip()
        if article not in DUPATTA_ARTICLES:
            continue
        image = row.get("image")
        if image is None:
            continue
        dest_path = dest / f"hfdupatta_{seen}_{saved:05d}.jpg"
        if dest_path.exists():
            continue
        try:
            image.convert("RGB").save(dest_path, format="JPEG", quality=90)
            saved += 1
        except Exception:  # noqa: BLE001
            continue
        if seen % 800 == 0:
            print(f"  scanned {seen}, extra dupattas {saved}", flush=True)
    print(f"extra dupattas {saved} (scanned {seen})", flush=True)
    return saved


def split_pool(seed: int = 31) -> dict[str, dict[str, int]]:
    rng = random.Random(seed)
    report: dict[str, dict[str, int]] = {"train": {}, "val": {}, "test": {}}
    for leaf in ("dupatta", "bag", "belt"):
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
    ap.add_argument("--scan", type=int, default=12000)
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
