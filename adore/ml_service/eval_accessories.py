"""Held-out eval of accessory classification (does not retrain lowerwear).

    .venv\\Scripts\\python.exe eval_accessories.py
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from PIL import Image

from app.clothing_classifier import classify_clothing
from app.fashionpedia_map import ACCESSORY_LEAVES

DEFAULT_DATA = Path(r"D:\fyp project\dataset") / "accessories_open" / "test"
OUT = Path(__file__).resolve().parent / "models" / "accessories8_live_eval.json"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
ALIASES = {
    "bag": {"bag"},
    "belt": {"belt"},
    "scarf": {"scarf", "dupatta"},
    "dupatta": {"dupatta", "scarf"},
    "hat": {"hat"},
    "hijab": {"hijab", "hat", "scarf"},
    "jewelry": {"jewelry", "watch"},
    "sunglasses": {"sunglasses"},
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA)
    ap.add_argument("--per-class", type=int, default=24)
    args = ap.parse_args()
    rows = []
    for leaf in ACCESSORY_LEAVES:
        folder = args.data / leaf
        if not folder.is_dir():
            continue
        paths = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in EXTS]
        for path in paths[: args.per_class]:
            with Image.open(path) as im:
                result = classify_clothing(im.convert("RGB"))
            pred = str(result.get("subcategory") or "unknown")
            ok = pred in ALIASES.get(leaf, {leaf})
            rows.append(
                {
                    "path": path.name,
                    "truth": leaf,
                    "pred": pred,
                    "ok": ok,
                    "confidence": float(result.get("confidence") or 0),
                    "source": result.get("source"),
                }
            )
    by = defaultdict(list)
    for row in rows:
        by[row["truth"]].append(row)
    summary = {
        "n": len(rows),
        "accuracy": (sum(1 for r in rows if r["ok"]) / max(len(rows), 1)),
        "per_class": {
            leaf: {
                "n": len(group),
                "accuracy": sum(1 for r in group if r["ok"]) / max(len(group), 1),
                "wrong": dict(
                    __import__("collections").Counter(
                        r["pred"] for r in group if not r["ok"]
                    )
                ),
            }
            for leaf, group in by.items()
        },
        "rows": rows,
    }
    OUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("n", "accuracy", "per_class")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
