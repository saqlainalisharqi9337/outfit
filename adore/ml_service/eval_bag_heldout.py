"""Held-out bag pipeline eval. Folder labels only — no filename tricks.

Uses the test split that was not used as training data:

    test/test/accessories/bag    → must predict bag
    test/test/accessories/hat    → must not become bag
    test/test/bottomwear/skirt   → must not become bag

Runs the same path as POST /analyze-clothing (classify_clothing), then
the accessory specialist alone so routing bugs are visible.

    .venv\\Scripts\\python.exe eval_bag_heldout.py
    .venv\\Scripts\\python.exe eval_bag_heldout.py --limit 80
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

from train_bag_shoes import DEFAULT_DATASET, EXTS, MODELS_DIR

SOURCES: tuple[tuple[str, str, str], ...] = (
    ("accessories", "bag", "bag"),
    ("accessories", "hat", "hat"),
    ("bottomwear", "skirt", "skirt"),
)


def _collect(root: Path, split: str) -> list[tuple[Path, str]]:
    base = root / split / split
    rows: list[tuple[Path, str]] = []
    for family, leaf, label in SOURCES:
        folder = base / family / leaf
        if not folder.is_dir():
            continue
        for path in folder.iterdir():
            if path.is_file() and path.suffix.lower() in EXTS:
                rows.append((path, label))
    return rows


def _cap(rows: list[tuple[Path, str]], limit: int | None) -> list[tuple[Path, str]]:
    if not limit or limit <= 0:
        return rows
    buckets: dict[str, list[tuple[Path, str]]] = {}
    for row in rows:
        buckets.setdefault(row[1], []).append(row)
    per = max(limit // max(len(buckets), 1), 1)
    out: list[tuple[Path, str]] = []
    for group in buckets.values():
        out.extend(group[:per])
    return out


def _score(rows: list[tuple[str, str]]) -> dict:
    labels = ("bag", "hat", "skirt")
    matrix = {src: Counter() for src in labels}
    for truth, pred in rows:
        if truth in matrix:
            matrix[truth][pred] += 1
    support = {name: sum(matrix[name].values()) for name in labels}
    correct = {name: matrix[name].get(name, 0) for name in labels}
    return {
        "support": support,
        "correct": correct,
        "recall": {
            name: (correct[name] / support[name]) if support[name] else 0.0
            for name in labels
        },
        "bag_as_hat": matrix["bag"].get("hat", 0),
        "bag_as_skirt": matrix["bag"].get("skirt", 0),
        "hat_as_bag": matrix["hat"].get("bag", 0),
        "skirt_as_bag": matrix["skirt"].get("bag", 0),
        "predicted": {name: dict(matrix[name]) for name in labels},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Held-out bag / hat / skirt eval")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--split", default="test")
    args = parser.parse_args()

    rows = _cap(_collect(args.dataset, args.split), args.limit)
    if not rows:
        raise SystemExit(f"No {args.split} images under {args.dataset}")

    from app.accessory_classifier import classify_accessory, status
    from app.clothing_classifier import classify_clothing

    specialist_pairs: list[tuple[str, str]] = []
    pipeline_pairs: list[tuple[str, str]] = []
    for path, truth in rows:
        image = Image.open(path).convert("RGB")
        specialist = classify_accessory(image) or {}
        pipeline = classify_clothing(image)
        specialist_pairs.append(
            (truth, str(specialist.get("subcategory") or "unknown"))
        )
        pipeline_pairs.append(
            (truth, str(pipeline.get("subcategory") or "unknown"))
        )
        print(
            f"{truth:6} -> pipeline={pipeline.get('subcategory')} "
            f"({float(pipeline.get('confidence') or 0):.2f} {pipeline.get('source')}) "
            f"specialist={specialist.get('subcategory')} "
            f"{path.name[:40]}",
            flush=True,
        )

    report = {
        "split": args.split,
        "images": len(rows),
        "accessory": status(),
        "specialist": _score(specialist_pairs),
        "pipeline": _score(pipeline_pairs),
        "notes": [
            "Ground truth is the folder name only.",
            "pipeline is classify_clothing (same as POST /analyze-clothing).",
            "Goal: bag_as_hat and bag_as_skirt near 0; hat/skirt must not collapse to bag.",
        ],
    }
    out = MODELS_DIR / "bag_heldout_eval.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print("Wrote", out)


if __name__ == "__main__":
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    sys.exit(main())
