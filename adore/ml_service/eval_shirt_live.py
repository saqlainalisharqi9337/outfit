"""Live pipeline eval for the new binary shirt detector.

    .venv\\Scripts\\python.exe eval_shirt_live.py
"""

from __future__ import annotations

import json
import os
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
    from app.shirt_gate import classify_shirt_gate, lock_shirt

    rows: list[tuple[str, Path]] = []
    local_shirts = _take(ROOT / "train" / "train" / "upperwear" / "shirt", 20)
    local_shirts += _take(ROOT / "train" / "train" / "upperwear" / "tshirt", 10)
    for path in local_shirts:
        rows.append(("shirt", path))
    extras = [
        ("dupatta", ROOT / "dupatta_gate" / "test" / "dupatta"),
        ("hat", ROOT / "hat_gate" / "test" / "hat"),
        ("bag", ROOT / "watch_gate" / "test" / "bag"),
        ("trousers", ROOT / "trousers_gate" / "test" / "trousers"),
        ("skirt", ROOT / "skirt_gate" / "test" / "skirt"),
        ("watch", ROOT / "watch_gate" / "test" / "watch"),
    ]
    for label, folder in extras:
        for path in _take(folder, 8):
            rows.append((label, path))
    if not rows:
        raise SystemExit("No eval images found.")

    specialist = Counter()
    pipeline = Counter()
    details: list[dict] = []
    for truth, path in rows:
        image = Image.open(path).convert("RGB")
        gate = classify_shirt_gate(image) or {}
        lock_shirt(image)
        result = classify_clothing(image)
        pred = str(result.get("subcategory") or "unknown")
        cat = str(result.get("category") or "")
        source = str(result.get("source") or "")
        gate_top = str(gate.get("subcategory") or "none")
        specialist[(truth, gate_top)] += 1
        pipeline[(truth, pred)] += 1
        details.append({"truth": truth, "pipeline": pred, "category": cat, "source": source})
        print(
            f"{truth:8} -> {cat}/{pred:10} src={source:14} "
            f"gate={gate_top:8} {path.name[:36]}",
            flush=True,
        )

    shirt_n = sum(1 for row in details if row["truth"] == "shirt")
    report = {
        "images": len(details),
        "shirt_n": shirt_n,
        "shirt_as_shirt": sum(
            1 for row in details if row["truth"] == "shirt" and row["pipeline"] == "shirt"
        ),
        "shirt_as_dupatta": sum(
            1 for row in details if row["truth"] == "shirt" and row["pipeline"] == "dupatta"
        ),
        "shirt_as_hat": sum(
            1 for row in details if row["truth"] == "shirt" and row["pipeline"] == "hat"
        ),
        "shirt_as_dress": sum(
            1 for row in details if row["truth"] == "shirt" and row["pipeline"] == "dress"
        ),
        "specialist": {f"{a}->{b}": n for (a, b), n in specialist.items()},
        "pipeline": {f"{a}->{b}": n for (a, b), n in pipeline.items()},
    }
    out = MODELS / "shirt_detector_live_eval.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    print("Wrote", out, flush=True)
    return 0


if __name__ == "__main__":
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    raise SystemExit(main())
