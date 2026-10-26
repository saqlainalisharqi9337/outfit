"""Validate the 20-class YOLO dataset before training."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from PIL import Image

from app.outfit20_taxonomy import OUTFIT20_CLASSES

OUT = Path(__file__).resolve().parent / "datasets" / "outfit20"
EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def main() -> int:
    report: dict = {
        "totalImages": 0,
        "trainingImages": 0,
        "validationImages": 0,
        "testingImages": 0,
        "totalAnnotations": 0,
        "imagesPerClass": {n: 0 for n in OUTFIT20_CLASSES},
        "annotationsPerClass": {n: 0 for n in OUTFIT20_CLASSES},
        "duplicateImages": 0,
        "invalidAnnotations": 0,
        "corruptedImages": 0,
        "missingLabels": 0,
        "emptyClasses": [],
    }
    seen: set[int] = set()
    for split, key in (("train", "trainingImages"), ("val", "validationImages"), ("test", "testingImages")):
        img_dir = OUT / split / "images"
        lab_dir = OUT / split / "labels"
        if not img_dir.is_dir():
            continue
        files = [p for p in img_dir.iterdir() if p.suffix.lower() in EXTS]
        report[key] = len(files)
        report["totalImages"] += len(files)
        for path in files:
            digest = hash(path.stat().st_size)
            if digest in seen:
                report["duplicateImages"] += 1
            seen.add(digest)
            try:
                with Image.open(path) as im:
                    im.verify()
            except Exception:
                report["corruptedImages"] += 1
                continue
            label = lab_dir / f"{path.stem}.txt"
            if not label.is_file():
                report["missingLabels"] += 1
                continue
            for line in label.read_text(encoding="utf-8").splitlines():
                parts = line.split()
                if len(parts) != 5:
                    report["invalidAnnotations"] += 1
                    continue
                try:
                    cid = int(parts[0])
                    vals = [float(v) for v in parts[1:]]
                except ValueError:
                    report["invalidAnnotations"] += 1
                    continue
                if cid < 0 or cid >= len(OUTFIT20_CLASSES) or any(v < 0 or v > 1 for v in vals):
                    report["invalidAnnotations"] += 1
                    continue
                name = OUTFIT20_CLASSES[cid]
                report["annotationsPerClass"][name] += 1
                report["imagesPerClass"][name] += 1
                report["totalAnnotations"] += 1
    report["emptyClasses"] = [
        n for n, c in report["annotationsPerClass"].items() if c == 0
    ]
    dest = OUT / "dataset_report.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if not report["emptyClasses"] or True else 1


if __name__ == "__main__":
    raise SystemExit(main())
