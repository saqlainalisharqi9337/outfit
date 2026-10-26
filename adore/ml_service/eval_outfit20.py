"""Per-class evaluation of the 20-class detector vs Fashionpedia baseline."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

from app.outfit20_taxonomy import OUTFIT20_CLASSES, SUBCATEGORY, class_id

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "datasets" / "outfit20"
OUT = ROOT / "models" / "improved"


def _labels(path: Path) -> set[str]:
    lab = DATA / "test" / "labels" / f"{path.stem}.txt"
    if not lab.is_file():
        return set()
    names = set()
    for line in lab.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if not parts:
            continue
        cid = int(parts[0])
        if 0 <= cid < len(OUTFIT20_CLASSES):
            names.add(OUTFIT20_CLASSES[cid])
    return names


def _predict(path: Path) -> set[str]:
    from app.outfit20_detector import detect_items, refine_footwear_and_wraps

    image = Image.open(path).convert("RGB")
    items = refine_footwear_and_wraps(image, detect_items(image))
    return {str(row.get("class")) for row in items if row.get("class")}


def main() -> int:
    img_dir = DATA / "test" / "images"
    files = sorted(p for p in img_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})
    tp = Counter()
    fp = Counter()
    fn = Counter()
    confusion: dict[str, Counter] = defaultdict(Counter)
    for path in files[:400]:
        truth = _labels(path)
        pred = _predict(path)
        for name in pred:
            if name in truth:
                tp[name] += 1
            else:
                fp[name] += 1
                for t in truth or {"none"}:
                    confusion[t][name] += 1
        for name in truth:
            if name not in pred:
                fn[name] += 1
    per_class = {}
    for name in OUTFIT20_CLASSES:
        p = tp[name] / max(1, tp[name] + fp[name])
        r = tp[name] / max(1, tp[name] + fn[name])
        f1 = 0.0 if p + r == 0 else 2 * p * r / (p + r)
        per_class[name] = {
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(f1, 4),
            "tp": tp[name],
            "fp": fp[name],
            "fn": fn[name],
            "subcategory": SUBCATEGORY[name],
        }
    report = {
        "images": min(len(files), 400),
        "perClass": per_class,
        "confusion": {k: dict(v) for k, v in confusion.items()},
        "detector": "outfit20 (improved if present, else Fashionpedia mapping)",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / "outfit20_eval.json"
    dest.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(per_class, indent=2))
    print("wrote", dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
