"""Production smoke: multi-sample classify + recommendation pairing."""

from __future__ import annotations

import json
import random
from pathlib import Path

from PIL import Image

from app.clothing_classifier import classify_clothing

DATASET = Path(r"D:\fyp project\dataset\test\test")
OUT = Path(__file__).resolve().parent / "models" / "production_smoke.json"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def can_form_outfit(items: list[dict]) -> tuple[bool, str]:
    cats = {i["category"] for i in items}
    if "dress" in cats and "footwear" in cats:
        return True, "dress+shoes"
    if "upperwear" in cats and "lowerwear" in cats and "footwear" in cats:
        return True, "top+bottom+shoes"
    return False, "incomplete"


def sample_paths(family: str, leaf: str, n: int = 8) -> list[Path]:
    folder = DATASET / family / leaf
    paths = [p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in EXTS]
    rng = random.Random(42)
    rng.shuffle(paths)
    return paths[:n]


def main() -> int:
    checks = [
        ("t-shirt", "upperwear", "tshirt", {"t-shirt"}),
        ("shirt", "upperwear", "shirt", {"shirt", "t-shirt"}),
        ("jacket", "upperwear", "jacket", {"jacket"}),
        ("dress", "one-piece", "dress", {"dress"}),
        ("trousers", "bottomwear", "pants", {"trousers", "jeans"}),
        ("shorts", "bottomwear", "shorts", {"shorts"}),
        ("skirt", "bottomwear", "skirt", {"skirt"}),
        ("hat", "accessories", "hat", {"hat"}),
        ("bag", "accessories", "bag", {"bag"}),
        ("heels", "footwear", "heels", {"heels", "sandals", "shoes", "flats"}),
    ]
    results = []
    for name, fam, leaf, ok in checks:
        preds = []
        for p in sample_paths(fam, leaf, 8):
            with Image.open(p) as im:
                preds.append(
                    str(classify_clothing(im.convert("RGB")).get("subcategory") or "unknown")
                )
        hits = sum(1 for p in preds if p in ok)
        acc = hits / max(len(preds), 1)
        results.append(
            {
                "item": name,
                "accuracy": round(acc, 3),
                "hits": hits,
                "n": len(preds),
                "preds": preds,
                "ok": acc >= 0.5,
            }
        )
        print(f"{name:10s} acc={acc:.0%} ({hits}/{len(preds)})  {preds}")

    demo = [
        {"category": "upperwear", "subcategory": "t-shirt"},
        {"category": "lowerwear", "subcategory": "trousers"},
        {"category": "footwear", "subcategory": "sneakers"},
    ]
    rec_ok, why = can_form_outfit(demo)
    payload = {
        "classify": results,
        "passed": sum(1 for r in results if r["ok"]),
        "total": len(results),
        "recommendation": {"ok": rec_ok, "why": why},
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("recommendation", why, "OK" if rec_ok else "FAIL")
    print(f"wrote {OUT}")
    return 0 if payload["passed"] >= 7 and rec_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
