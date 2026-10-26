"""Held-out evaluation for the 6-class upperwear/dress model."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from app.garment_classifier import classify_garment, loaded_classes

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "datasets" / "upperwear6"
MODELS = ROOT / "models"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def main() -> int:
    from app import garment_classifier

    garment_classifier.reset()
    classes = loaded_classes()
    print("loaded", classes)
    rows = []
    correct = 0
    n = 0
    per = {c: {"tp": 0, "n": 0} for c in classes}
    test_dir = DATA / "test"
    if not test_dir.is_dir():
        raise SystemExit("no test split")
    for folder in sorted(test_dir.iterdir()):
        if not folder.is_dir():
            continue
        truth = folder.name
        for path in folder.iterdir():
            if path.suffix.lower() not in EXTS:
                continue
            with Image.open(path) as im:
                pred = classify_garment(im.convert("RGB"))
            label = (pred or {}).get("subcategory") or "unknown"
            n += 1
            if truth in per:
                per[truth]["n"] += 1
            ok = label == truth
            if ok:
                correct += 1
                if truth in per:
                    per[truth]["tp"] += 1
            rows.append({"file": path.name, "actual": truth, "predicted": label, "ok": ok})
    report = {
        "accuracy": round(correct / max(1, n), 4),
        "n": n,
        "perClass": {
            k: {
                "recall": round(v["tp"] / max(1, v["n"]), 4),
                "support": v["n"],
            }
            for k, v in per.items()
        },
        "classes": classes,
    }
    MODELS.joinpath("upperwear6_live_eval.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
