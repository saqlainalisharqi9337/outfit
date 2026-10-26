"""Live pipeline eval for sneakers vs hat vs flats vs heels.

    .venv\\Scripts\\python.exe eval_sneakers_live.py
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
    from app.sneakers_gate import classify_sneakers_gate

    rows: list[tuple[str, Path]] = []
    for path in _take(ROOT / "train" / "train" / "footwear" / "sneakers", 24):
        rows.append(("sneakers", path))
    extras = [
        ("hat", ROOT / "train" / "train" / "accessories" / "hat"),
        ("flats", ROOT / "train" / "train" / "footwear" / "flats"),
        ("heels", ROOT / "train" / "train" / "footwear" / "heels"),
        ("shirt", ROOT / "train" / "train" / "upperwear" / "shirt"),
        ("t-shirt", ROOT / "train" / "train" / "upperwear" / "tshirt"),
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
        gate = classify_sneakers_gate(image) or {}
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

    sneaker_n = sum(1 for row in details if row["truth"] == "sneakers")
    report = {
        "images": len(details),
        "sneakers_n": sneaker_n,
        "sneakers_as_sneakers": sum(
            1 for row in details if row["truth"] == "sneakers" and row["pipeline"] == "sneakers"
        ),
        "sneakers_as_hat": sum(
            1 for row in details if row["truth"] == "sneakers" and row["pipeline"] == "hat"
        ),
        "sneakers_as_flats": sum(
            1 for row in details if row["truth"] == "sneakers" and row["pipeline"] == "flats"
        ),
        "sneakers_as_footwear": sum(
            1
            for row in details
            if row["truth"] == "sneakers" and row["category"] == "footwear"
        ),
        "hat_as_hat": sum(
            1 for row in details if row["truth"] == "hat" and row["pipeline"] == "hat"
        ),
        "hat_as_sneakers": sum(
            1 for row in details if row["truth"] == "hat" and row["pipeline"] == "sneakers"
        ),
        "flats_as_flats": sum(
            1 for row in details if row["truth"] == "flats" and row["pipeline"] == "flats"
        ),
        "flats_as_sneakers": sum(
            1 for row in details if row["truth"] == "flats" and row["pipeline"] == "sneakers"
        ),
        "heels_as_heels": sum(
            1 for row in details if row["truth"] == "heels" and row["pipeline"] == "heels"
        ),
        "heels_as_sneakers": sum(
            1 for row in details if row["truth"] == "heels" and row["pipeline"] == "sneakers"
        ),
        "jacket_as_jacket": sum(
            1 for row in details if row["truth"] == "jacket" and row["pipeline"] == "jacket"
        ),
        "specialist": {f"{a}->{b}": n for (a, b), n in specialist.items()},
        "pipeline": {f"{a}->{b}": n for (a, b), n in pipeline.items()},
    }
    out = MODELS / "sneakers_gate_live_eval.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    print("Wrote", out, flush=True)
    return 0


if __name__ == "__main__":
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    raise SystemExit(main())
