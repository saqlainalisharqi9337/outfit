"""End-to-end P/R/F1 for plan-B classes on the held-out test split.

Evaluates classify_clothing() on:
  shirt, t-shirt, jacket, hat, bag, heels

Does not touch lowerwear training or labels.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

from PIL import Image
from tqdm import tqdm

from app.clothing_classifier import classify_clothing

DATASET = Path(r"D:\fyp project\dataset")
OUT = Path(__file__).resolve().parent / "models" / "plan_b_eval.json"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

# (family, leaf_folder, expected_subcategory)
TARGETS = (
    ("upperwear", "shirt", "shirt"),
    ("upperwear", "tshirt", "t-shirt"),
    ("upperwear", "jacket", "jacket"),
    ("accessories", "hat", "hat"),
    ("accessories", "bag", "bag"),
    ("footwear", "heels", "heels"),
)


def collect(max_per: int | None = 120) -> list[tuple[Path, str]]:
    base = DATASET / "test" / "test"
    rows: list[tuple[Path, str]] = []
    rng = random.Random(42)
    for family, leaf, label in TARGETS:
        folder = base / family / leaf
        if not folder.is_dir():
            print(f"MISSING {folder}")
            continue
        paths = [
            p
            for p in folder.rglob("*")
            if p.is_file() and p.suffix.lower() in EXTS
        ]
        rng.shuffle(paths)
        if max_per:
            paths = paths[:max_per]
        rows.extend((p, label) for p in paths)
        print(f"{label:8s} n={len(paths)}")
    return rows


def metrics(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict:
    per = {}
    for lab in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == lab and p == lab)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != lab and p == lab)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == lab and p != lab)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        per[lab] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "support": sum(1 for t in y_true if t == lab),
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }
    return per


def main() -> int:
    rows = collect(120)
    y_true: list[str] = []
    y_pred: list[str] = []
    confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for path, truth in tqdm(rows, desc="plan-b eval"):
        with Image.open(path) as im:
            out = classify_clothing(im.convert("RGB"))
        pred = str(out.get("subcategory") or "unknown")
        y_true.append(truth)
        y_pred.append(pred)
        confusion[truth][pred] += 1

    labels = [t[2] for t in TARGETS]
    per = metrics(y_true, y_pred, labels)
    payload = {
        "n": len(rows),
        "per_class": per,
        "confusion": {k: dict(v) for k, v in confusion.items()},
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(per, indent=2))
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
