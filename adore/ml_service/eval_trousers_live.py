"""Live pipeline eval for trousers vs dress vs shirt.

Held-out trousers_gate test folders plus a few bags/hats/watches so
accessory specialists are not regressed.

    .venv\\Scripts\\python.exe eval_trousers_live.py
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT = Path(r"D:\fyp project\dataset")
MODELS = Path(__file__).resolve().parent / "models"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def _take(folder: Path, limit: int) -> list[Path]:
    if not folder.is_dir():
        return []
    files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in EXTS]
    files.sort(key=lambda p: p.name)
    return files[:limit]


def main() -> int:
    from app.clothing_classifier import classify_clothing
    from app.trousers_gate import classify_trousers_gate, lock_trousers

    rows: list[tuple[str, Path]] = []
    for leaf in ("trousers", "dress", "shirt"):
        for path in _take(ROOT / "trousers_gate" / "test" / leaf, 24):
            rows.append((leaf, path))
    extras = [
        ("bag", ROOT / "watch_gate" / "test" / "bag"),
        ("hat", ROOT / "hat_gate" / "test" / "hat"),
        ("watch", ROOT / "watch_gate" / "test" / "watch"),
        ("dupatta", ROOT / "dupatta_gate" / "test" / "dupatta"),
        ("shorts", ROOT / "test" / "test" / "bottomwear" / "shorts"),
    ]
    for label, folder in extras:
        for path in _take(folder, 8):
            rows.append((label, path))
    if not rows:
        raise SystemExit("No eval images found. Run prepare_trousers_gate.py first.")

    specialist = Counter()
    pipeline = Counter()
    details: list[dict] = []
    for truth, path in rows:
        image = Image.open(path).convert("RGB")
        gate = classify_trousers_gate(image) or {}
        locked = lock_trousers(image)
        result = classify_clothing(image)
        pred = str(result.get("subcategory") or "unknown")
        cat = str(result.get("category") or "")
        source = str(result.get("source") or "")
        gate_top = str(gate.get("subcategory") or "none")
        specialist[(truth, gate_top)] += 1
        pipeline[(truth, pred)] += 1
        details.append(
            {
                "truth": truth,
                "file": path.name,
                "pipeline": pred,
                "category": cat,
                "source": source,
                "gate": gate_top,
                "locked": locked is not None,
                "confidence": float(result.get("confidence") or 0),
            }
        )
        print(
            f"{truth:8} -> {cat}/{pred:10} src={source:14} "
            f"gate={gate_top:8} {path.name[:36]}",
            flush=True,
        )

    trousers_as_trousers = sum(
        1 for row in details if row["truth"] == "trousers" and row["pipeline"] == "trousers"
    )
    trousers_n = sum(1 for row in details if row["truth"] == "trousers")
    trousers_as_dress = sum(
        1 for row in details if row["truth"] == "trousers" and row["pipeline"] == "dress"
    )
    trousers_as_shirt = sum(
        1
        for row in details
        if row["truth"] == "trousers" and row["pipeline"] in {"shirt", "t-shirt"}
    )
    report = {
        "images": len(details),
        "trousers_n": trousers_n,
        "trousers_as_trousers": trousers_as_trousers,
        "trousers_as_dress": trousers_as_dress,
        "trousers_as_shirt": trousers_as_shirt,
        "specialist": {f"{a}->{b}": n for (a, b), n in specialist.items()},
        "pipeline": {f"{a}->{b}": n for (a, b), n in pipeline.items()},
    }
    out = MODELS / "trousers_gate_live_eval.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    print("Wrote", out, flush=True)
    return 0


if __name__ == "__main__":
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    raise SystemExit(main())
