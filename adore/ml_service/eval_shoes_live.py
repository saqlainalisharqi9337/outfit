"""Live pipeline eval for shoes vs heels vs sneakers vs flats.

    .venv\\Scripts\\python.exe eval_shoes_live.py
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
    from app.shoes_gate import classify_shoes_gate

    rows: list[tuple[str, Path]] = []
    for path in _take(ROOT / "train" / "train" / "footwear" / "shoes", 24):
        rows.append(("shoes", path))
    extras = [
        ("sneakers", ROOT / "train" / "train" / "footwear" / "sneakers"),
        ("heels", ROOT / "train" / "train" / "footwear" / "heels"),
        ("flats", ROOT / "train" / "train" / "footwear" / "flats"),
        ("hat", ROOT / "train" / "train" / "accessories" / "hat"),
        ("shirt", ROOT / "train" / "train" / "upperwear" / "shirt"),
        ("jacket", ROOT / "train" / "train" / "upperwear" / "jacket"),
        ("bag", ROOT / "watch_gate" / "test" / "bag"),
        ("trousers", ROOT / "trousers_gate" / "test" / "trousers"),
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
        gate = classify_shoes_gate(image) or {}
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

    shoes_n = sum(1 for row in details if row["truth"] == "shoes")
    report = {
        "images": len(details),
        "shoes_n": shoes_n,
        "shoes_as_shoes": sum(
            1 for row in details if row["truth"] == "shoes" and row["pipeline"] == "shoes"
        ),
        "shoes_as_heels": sum(
            1 for row in details if row["truth"] == "shoes" and row["pipeline"] == "heels"
        ),
        "shoes_as_sneakers": sum(
            1 for row in details if row["truth"] == "shoes" and row["pipeline"] == "sneakers"
        ),
        "shoes_as_shirt": sum(
            1 for row in details if row["truth"] == "shoes" and row["pipeline"] == "shirt"
        ),
        "shoes_as_footwear": sum(
            1
            for row in details
            if row["truth"] == "shoes" and row["category"] == "footwear"
        ),
        "sneakers_as_sneakers": sum(
            1 for row in details if row["truth"] == "sneakers" and row["pipeline"] == "sneakers"
        ),
        "sneakers_as_shoes": sum(
            1 for row in details if row["truth"] == "sneakers" and row["pipeline"] == "shoes"
        ),
        "heels_as_heels": sum(
            1 for row in details if row["truth"] == "heels" and row["pipeline"] == "heels"
        ),
        "heels_as_shoes": sum(
            1 for row in details if row["truth"] == "heels" and row["pipeline"] == "shoes"
        ),
        "flats_as_flats": sum(
            1 for row in details if row["truth"] == "flats" and row["pipeline"] == "flats"
        ),
        "jacket_as_jacket": sum(
            1 for row in details if row["truth"] == "jacket" and row["pipeline"] == "jacket"
        ),
        "specialist": {f"{a}->{b}": n for (a, b), n in specialist.items()},
        "pipeline": {f"{a}->{b}": n for (a, b), n in pipeline.items()},
    }
    out = MODELS / "shoes_gate_live_eval.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    print("Wrote", out, flush=True)
    return 0


if __name__ == "__main__":
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    raise SystemExit(main())
