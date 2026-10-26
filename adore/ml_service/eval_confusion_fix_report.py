"""Per-class precision/recall report for Adore clothing classification.

Samples the dataset test split, runs classify_clothing, and writes
models/confusion_fix_report.json. Does not retrain lowerwear or change
sneaker logic — evaluation only.

Usage (from ml_service):

    .venv\\Scripts\\python.exe eval_confusion_fix_report.py
    .venv\\Scripts\\python.exe eval_confusion_fix_report.py --per-class 24
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

from PIL import Image

from app.clothing_classifier import classify_clothing
from app.config import get_settings

DATASET = Path(r"D:\fyp project\dataset\test\test")
OUT = Path(__file__).resolve().parent / "models" / "confusion_fix_report.json"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

# Ground-truth folder → acceptable prediction set (aliases).
CHECKS: list[tuple[str, str, str, set[str]]] = [
    ("jacket", "upperwear", "jacket", {"jacket"}),
    ("shirt", "upperwear", "shirt", {"shirt", "t-shirt"}),
    ("t-shirt", "upperwear", "tshirt", {"t-shirt", "shirt"}),
    ("hat", "accessories", "hat", {"hat"}),
    ("bag", "accessories", "bag", {"bag"}),
    ("heels", "footwear", "heels", {"heels", "sandals"}),
    ("sandals", "footwear", "sandals", {"sandals", "heels", "flats"}),
    # Regression guards (must not regress):
    ("trousers", "bottomwear", "pants", {"trousers", "jeans"}),
    ("shorts", "bottomwear", "shorts", {"shorts"}),
    ("skirt", "bottomwear", "skirt", {"skirt"}),
    ("sneakers", "footwear", "sneakers", {"sneakers", "shoes"}),
]


def sample_paths(family: str, leaf: str, n: int, seed: int) -> list[Path]:
    folder = DATASET / family / leaf
    if not folder.is_dir():
        return []
    paths = [p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in EXTS]
    rng = random.Random(seed)
    rng.shuffle(paths)
    return paths[:n]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-class", type=int, default=20)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    threshold = float(get_settings().human_review_min_confidence)
    rows = []
    for name, fam, leaf, ok in CHECKS:
        preds: list[str] = []
        confs: list[float] = []
        reviews = 0
        for path in sample_paths(fam, leaf, args.per_class, args.seed):
            with Image.open(path) as im:
                result = classify_clothing(im.convert("RGB"))
            pred = str(result.get("subcategory") or "unknown")
            preds.append(pred)
            confs.append(float(result.get("confidence") or 0))
            if result.get("needsHumanReview"):
                reviews += 1
        hits = sum(1 for p in preds if p in ok)
        n = max(len(preds), 1)
        # Confusion tally: wrong pred → count
        wrong = defaultdict(int)
        for p in preds:
            if p not in ok:
                wrong[p] += 1
        rows.append(
            {
                "class": name,
                "support": len(preds),
                "accuracy": round(hits / n, 4),
                "hits": hits,
                "needsHumanReviewRate": round(reviews / n, 4),
                "meanConfidence": round(sum(confs) / n, 4) if confs else 0.0,
                "wrongAs": dict(wrong),
                "preds": preds,
                "okLabels": sorted(ok),
                "regressionGuard": name in {"trousers", "shorts", "skirt", "sneakers"},
            }
        )
        print(
            f"{name:10s} acc={hits / n:.0%} ({hits}/{len(preds)})  "
            f"review={reviews / n:.0%}  wrong={dict(wrong)}"
        )

    payload = {
        "humanReviewThreshold": threshold,
        "perClass": rows,
        "summary": {
            "classes": len(rows),
            "macroAccuracy": round(
                sum(r["accuracy"] for r in rows) / max(len(rows), 1), 4
            ),
            "confusionTargets": {
                r["class"]: r["accuracy"]
                for r in rows
                if r["class"] in {"jacket", "hat", "bag", "heels", "t-shirt"}
            },
            "regressionGuards": {
                r["class"]: r["accuracy"]
                for r in rows
                if r["regressionGuard"]
            },
        },
        "notes": [
            "Uses existing Adore dataset + previously imported CC0 clothing-dataset images.",
            "DeepFashion2 / Fashionpedia / iMaterialist were not bundled; Fashion-MNIST is too low-res for this pipeline.",
            "Lowerwear and sneaker classification logic were not modified.",
            f"Predictions with confidence < {threshold} set needsHumanReview=true.",
        ],
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
