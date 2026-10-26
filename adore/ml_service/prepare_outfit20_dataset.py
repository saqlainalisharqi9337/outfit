"""Build the 20-class YOLO dataset from local Adore folders.

Does not overwrite the original Fashionpedia checkpoint.
Single-item product photos get a near-full-frame box (the item IS the image).
"""

from __future__ import annotations

import hashlib
import json
import random
import shutil
from collections import defaultdict
from pathlib import Path

from app.outfit20_taxonomy import OUTFIT20_CLASSES, class_id, resolve_label

ROOT = Path(__file__).resolve().parent
DATASET_SRC = Path(r"D:\fyp project\dataset")
USER_LABELED = ROOT / "datasets" / "user_labeled"
OUT = ROOT / "datasets" / "outfit20"
ORIGINAL = ROOT / "models" / "original"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
TRAIN_CAP = 80
VAL_CAP = 16
TEST_CAP = 16
PER_CLASS_SCAN = TRAIN_CAP + VAL_CAP + TEST_CAP + 8

FOLDER_SOURCES: list[tuple[str, str]] = [
    ("train/train/accessories/bag", "accessories_bag"),
    ("train/train/accessories/hat", "accessories_hat"),
    ("train/train/bottomwear/pants", "lowerwear_trousers"),
    ("train/train/bottomwear/shorts", "lowerwear_shorts"),
    ("train/train/bottomwear/skirt", "lowerwear_skirt"),
    ("train/train/footwear/flats", "footwear_flats"),
    ("train/train/footwear/shoes", "footwear_shoes"),
    ("train/train/footwear/sneakers", "footwear_sneakers"),
    ("train/train/one-piece/dress", "one_piece_dress"),
    ("train/train/upperwear/jacket", "upperwear_jacket"),
    ("train/train/upperwear/shirt", "upperwear_shirt"),
    ("train/train/upperwear/tshirt", "upperwear_tshirt"),
    ("hat_gate/test/hat", "accessories_hat"),
    ("dupatta_gate/test/dupatta", "accessories_dupatta"),
    ("watch_gate/test/watch", "accessories_watch"),
    ("skirt_gate/test/belt", "accessories_belt"),
    ("watch_gate/test/bag", "accessories_bag"),
    ("bag_gate/test/bag", "accessories_bag"),
    ("flats_gate/test/flats", "footwear_flats"),
    ("shoes_gate/test/shoes", "footwear_shoes"),
    ("sneakers_gate/test/sneakers", "footwear_sneakers"),
    ("jacket_gate/test/jacket", "upperwear_jacket"),
    ("shirt_gate/test/shirt", "upperwear_shirt"),
    ("tshirt_gate/test/t-shirt", "upperwear_tshirt"),
    ("trousers_gate/test/trousers", "lowerwear_trousers"),
    ("skirt_gate/test/skirt", "lowerwear_skirt"),
]


def _files(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    out = [p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in EXTS]
    out.sort(key=lambda p: p.as_posix())
    return out


def _digest(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        h.update(fh.read(64 * 1024))
    return h.hexdigest()


def _write_label(path: Path, class_name: str) -> None:
    cid = class_id(class_name)
    path.write_text(f"{cid} 0.5 0.5 0.92 0.92\n", encoding="utf-8")


def _copy(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        return
    try:
        os_link = getattr(src, "hardlink_to", None)
        if os_link:
            dest.hardlink_to(src)
            return
    except OSError:
        pass
    shutil.copy2(src, dest)


def backup_original() -> None:
    ORIGINAL.mkdir(parents=True, exist_ok=True)
    src = ROOT / "models" / "yolov8n-fashionpedia-1.torchscript"
    dest = ORIGINAL / "yolov8n-fashionpedia-1.torchscript"
    if src.is_file() and not dest.is_file():
        shutil.copy2(src, dest)


def collect() -> dict[str, list[Path]]:
    by_class: dict[str, list[Path]] = defaultdict(list)
    seen: set[str] = set()
    for rel, name in FOLDER_SOURCES:
        for path in _files(DATASET_SRC / rel):
            if len(by_class[name]) >= PER_CLASS_SCAN:
                break
            key = _digest(path)
            if key in seen:
                continue
            seen.add(key)
            by_class[name].append(path)
    return by_class


def collect_user() -> dict[str, list[Path]]:
    """Photos you labeled as pants / t-shirt / … always go into training."""
    by_class: dict[str, list[Path]] = defaultdict(list)
    if not USER_LABELED.is_dir():
        return by_class
    for child in sorted(USER_LABELED.iterdir()):
        if not child.is_dir():
            continue
        name = resolve_label(child.name)
        if name is None:
            continue
        by_class[name].extend(_files(child))
    return by_class


def split_and_write(
    by_class: dict[str, list[Path]],
    user_by_class: dict[str, list[Path]] | None = None,
) -> dict:
    random.seed(20)
    for split in ("train", "val", "test"):
        (OUT / split / "images").mkdir(parents=True, exist_ok=True)
        (OUT / split / "labels").mkdir(parents=True, exist_ok=True)
    report = {"classes": {}, "splits": {"train": 0, "val": 0, "test": 0}}
    for name in OUTFIT20_CLASSES:
        files = list(by_class.get(name, []))
        random.shuffle(files)
        test = files[:TEST_CAP]
        val = files[TEST_CAP : TEST_CAP + VAL_CAP]
        train = files[TEST_CAP + VAL_CAP : TEST_CAP + VAL_CAP + TRAIN_CAP]
        extra = list((user_by_class or {}).get(name, []))
        train = extra + [p for p in train if p not in extra]
        buckets = {"train": train, "val": val, "test": test}
        report["classes"][name] = {k: len(v) for k, v in buckets.items()}
        for split, rows in buckets.items():
            for i, src in enumerate(rows):
                stem = f"{name}_{i:04d}{src.suffix.lower()}"
                dest = OUT / split / "images" / stem
                _copy(src, dest)
                _write_label(OUT / split / "labels" / f"{dest.stem}.txt", name)
                report["splits"][split] += 1
    yaml = OUT / "data.yaml"
    names = "\n".join(f"  {i}: {n}" for i, n in enumerate(OUTFIT20_CLASSES))
    yaml.write_text(
        f"path: {OUT.as_posix()}\ntrain: train/images\nval: val/images\n"
        f"test: test/images\nnames:\n{names}\n",
        encoding="utf-8",
    )
    (OUT / "dataset_build.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    backup_original()
    by_class = collect()
    user_by_class = collect_user()
    report = split_and_write(by_class, user_by_class)
    report["userLabeled"] = {k: len(v) for k, v in user_by_class.items() if v}
    (OUT / "dataset_build.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    print("wrote", OUT / "data.yaml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
