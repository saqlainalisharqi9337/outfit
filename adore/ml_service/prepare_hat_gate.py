"""Build hat vs bag vs shirt training folders from open images.

Hats:
  * local Adore ``accessories/hat``
  * Fashionpedia hat crops already in ``accessories_open``
  * Wikimedia Commons CC baseball cap / beanie / sun hat / fedora

Hard negatives (the two live mistakes):
  * local ``accessories/bag``  (do not retrain bag_gate)
  * local ``upperwear/shirt`` and ``tshirt``

    .venv\\Scripts\\python.exe prepare_hat_gate.py
"""

from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
LOCAL = Path(r"D:\fyp project\dataset")
OPEN = LOCAL / "accessories_open"
OUT = LOCAL / "hat_gate"
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
    hats = 0
    for split in ("train", "val", "test"):
        hats += _copy_folder(
            LOCAL / split / split / "accessories" / "hat",
            OUT / "pool" / "hat",
            f"local_{split}",
            limit,
        )
        if hats >= limit:
            break
    counts["hat_local"] = min(hats, limit)
    extra = OPEN / "pool" / "hat"
    counts["hat_fashionpedia"] = _copy_folder(extra, OUT / "pool" / "hat", "fp", limit)
    for split in ("train", "val", "test"):
        counts["hat_fashionpedia"] += _copy_folder(
            OPEN / split / "hat", OUT / "pool" / "hat", f"fp_{split}", limit
        )
    counts["bag"] = _copy_folder(
        LOCAL / "train" / "train" / "accessories" / "bag",
        OUT / "pool" / "bag",
        "local_bag",
        limit,
    )
    shirts = _copy_folder(
        LOCAL / "train" / "train" / "upperwear" / "shirt",
        OUT / "pool" / "shirt",
        "local_shirt",
        limit // 2 + 1,
    )
    shirts += _copy_folder(
        LOCAL / "train" / "train" / "upperwear" / "tshirt",
        OUT / "pool" / "shirt",
        "local_tshirt",
        limit // 2 + 1,
    )
    counts["shirt"] = min(shirts, limit)
    return counts


def from_wikimedia(limit: int) -> int:
    dest = OUT / "pool" / "hat"
    dest.mkdir(parents=True, exist_ok=True)
    existing = len(list(dest.glob("wiki_*")))
    if existing >= min(80, limit):
        print(f"Wikimedia skip, already {existing} hat images")
        return 0
    try:
        from download_wikimedia_weak_classes import file_info, search_files, UA
    except Exception as exc:  # noqa: BLE001
        print("Wikimedia helper missing:", exc, flush=True)
        return 0
    import urllib.request

    queries = ("baseball cap", "beanie hat", "sun hat", "fedora hat")
    saved = 0
    print("Downloading Wikimedia Commons hats…", flush=True)
    for query in queries:
        try:
            titles = search_files(query, limit=24)
            infos = file_info(titles)
        except Exception as exc:  # noqa: BLE001
            print(f"  {query} failed:", exc, flush=True)
            continue
        for info in infos:
            url = info.get("url") or info.get("thumburl")
            if not url:
                continue
            dest_path = dest / f"wiki_{query.replace(' ', '_')}_{saved:04d}.jpg"
            if dest_path.exists():
                continue
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=25) as resp:
                    raw = resp.read()
                dest_path.write_bytes(raw)
                with Image.open(dest_path) as im:
                    im.convert("RGB").save(dest_path, format="JPEG", quality=90)
                saved += 1
            except Exception:  # noqa: BLE001
                if dest_path.exists():
                    dest_path.unlink()
                continue
            if existing + saved >= min(80, limit):
                break
        if existing + saved >= min(80, limit):
            break
    print(f"Wikimedia hats added: {saved}", flush=True)
    return saved


def split_pool(seed: int = 17) -> dict[str, dict[str, int]]:
    rng = random.Random(seed)
    report: dict[str, dict[str, int]] = {"train": {}, "val": {}, "test": {}}
    for leaf in ("hat", "bag", "shirt"):
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
    ap.add_argument("--skip-wiki", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    print("local:", copy_local(args.limit), flush=True)
    if not args.skip_wiki:
        try:
            print("wikimedia:", from_wikimedia(args.limit), flush=True)
        except Exception as exc:  # noqa: BLE001
            print("wikimedia failed:", exc, flush=True)
    print("splits:", split_pool(), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
