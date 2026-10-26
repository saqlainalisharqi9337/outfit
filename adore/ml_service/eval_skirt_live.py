"""Live pipeline eval for skirt vs belt vs hat.

    .venv\\Scripts\\python.exe eval_skirt_live.py
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
    from app.skirt_gate import classify_skirt_gate, lock_skirt

    rows: list[tuple[str, Path]] = []
    for leaf in ("skirt", "belt", "hat"):
        for path in _take(ROOT / "skirt_gate" / "test" / leaf, 24):
            rows.append((leaf, path))
    extras = [
        ("bag", ROOT / "watch_gate" / "test" / "bag"),
        ("watch", ROOT / "watch_gate" / "test" / "watch"),
        ("dupatta", ROOT / "dupatta_gate" / "test" / "dupatta"),
        ("trousers", ROOT / "trousers_gate" / "test" / "trousers"),
    ]
    for label, folder in extras:
        for path in _take(folder, 8):
            rows.append((label, path))
    if not rows:
        raise SystemExit("No eval images found. Run prepare_skirt_gate.py first.")

    specialist = Counter()
    pipeline = Counter()
    details: list[dict] = []
    for truth, path in rows:
        image = Image.open(path).convert("RGB")
        gate = classify_skirt_gate(image) or {}
        locked = lock_skirt(image)
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
            }
        )
        print(
            f"{truth:8} -> {cat}/{pred:10} src={source:14} "
            f"gate={gate_top:8} {path.name[:36]}",
            flush=True,
        )

    skirt_n = sum(1 for row in details if row["truth"] == "skirt")
    report = {
        "images": len(details),
        "skirt_n": skirt_n,
        "skirt_as_skirt": sum(
            1 for row in details if row["truth"] == "skirt" and row["pipeline"] == "skirt"
        ),
        "skirt_as_belt": sum(
            1 for row in details if row["truth"] == "skirt" and row["pipeline"] == "belt"
        ),
        "skirt_as_hat": sum(
            1 for row in details if row["truth"] == "skirt" and row["pipeline"] == "hat"
        ),
        "specialist": {f"{a}->{b}": n for (a, b), n in specialist.items()},
        "pipeline": {f"{a}->{b}": n for (a, b), n in pipeline.items()},
    }
    out = MODELS / "skirt_gate_live_eval.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    print("Wrote", out, flush=True)
    return 0


if __name__ == "__main__":
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    raise SystemExit(main())
