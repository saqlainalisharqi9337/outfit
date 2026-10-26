"""Score the synthetic colour suite and write an error-analysis report."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PIL import Image

from app.color_analysis import analyze_garment_colors, render_debug_collage

import importlib.util

_fix = ROOT / "tests" / "color_fixtures.py"
_spec = importlib.util.spec_from_file_location("color_fixtures", _fix)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
CASES = _mod.CASES

REPORTS = ROOT / "reports"
DEBUG_DIR = REPORTS / "color_debug"


def _hit(value: str, allowed: set[str]) -> bool:
    return value in allowed


def _secondary_hit(predicted: list[str], allowed: set[str], minimum: int) -> bool:
    if not allowed:
        return True
    matched = [name for name in predicted if name in allowed]
    return len(set(matched)) >= minimum


def evaluate() -> dict:
    rows = []
    primary_ok = 0
    secondary_ok = 0
    multi_ok = 0
    multi_n = 0
    tp = Counter()
    fp = Counter()
    fn = Counter()
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)

    for case in CASES:
        image: Image.Image = case["builder"]()
        bbox = [0.22, 0.12, 0.78, 0.88] if case["id"] == "black_shirt_blue_wall" else None
        pred = analyze_garment_colors(image, bbox=bbox, debug=True)
        actual_primary = case["primary"]
        actual_secondary = set(case.get("secondary") or [])
        min_secondary = int(case.get("min_secondary") or (1 if actual_secondary else 0))
        predicted_names = [
            pred.primary_color,
            *pred.secondary_colors,
            *pred.accent_colors,
        ]
        p_ok = _hit(pred.primary_color, actual_primary)
        if case.get("forbidden") and pred.primary_color in case["forbidden"]:
            p_ok = False
        if case.get("forbidden_primary") and pred.primary_color in case["forbidden_primary"]:
            p_ok = False
        s_ok = _secondary_hit(
            pred.secondary_colors + pred.accent_colors,
            actual_secondary,
            min_secondary,
        )
        wants_multi = bool(actual_secondary) or min_secondary > 0
        if wants_multi:
            multi_n += 1
            if pred.is_multicolor and s_ok:
                multi_ok += 1
        if p_ok:
            primary_ok += 1
        if s_ok:
            secondary_ok += 1

        predicted_set = {n for n in predicted_names}
        allowed = set(actual_primary) | set(actual_secondary)
        for name in predicted_set:
            if name in allowed:
                tp[name] += 1
            else:
                fp[name] += 1
        if not (predicted_set & actual_primary):
            fn[next(iter(actual_primary))] += 1
        if actual_secondary and min_secondary:
            if len(predicted_set & actual_secondary) < min_secondary:
                fn[next(iter(actual_secondary))] += 1

        collage = render_debug_collage(image, pred)
        collage_path = DEBUG_DIR / f"{case['id']}.png"
        collage.save(collage_path)

        rows.append(
            {
                "id": case["id"],
                "item": case["item"],
                "kind": case["kind"],
                "actual": {
                    "primary": sorted(actual_primary),
                    "secondary": sorted(actual_secondary),
                },
                "predicted": {
                    "primary": pred.primary_color,
                    "secondary": pred.secondary_colors,
                    "accent": pred.accent_colors,
                    "distribution": pred.color_distribution,
                    "pattern": pred.pattern,
                    "isMulticolor": pred.is_multicolor,
                },
                "primaryOk": p_ok,
                "secondaryOk": s_ok,
                "debugImage": str(collage_path),
            }
        )

    n = max(1, len(CASES))
    precision_den = sum(tp.values()) + sum(fp.values())
    recall_den = sum(tp.values()) + sum(fn.values())
    report = {
        "n": n,
        "primaryColorAccuracy": round(primary_ok / n, 3),
        "secondaryColorAccuracy": round(secondary_ok / n, 3),
        "multiColorDetectionAccuracy": round(multi_ok / max(1, multi_n), 3),
        "colorDetectionPrecision": round(sum(tp.values()) / max(1, precision_den), 3),
        "colorDetectionRecall": round(sum(tp.values()) / max(1, recall_den), 3),
        "perColor": {
            name: {
                "tp": int(tp[name]),
                "fp": int(fp[name]),
                "fn": int(fn[name]),
            }
            for name in sorted(set(tp) | set(fp) | set(fn))
        },
        "cases": rows,
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "color_error_analysis.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    lines = [
        "# Colour error analysis",
        "",
        f"- Primary accuracy: **{report['primaryColorAccuracy']:.0%}**",
        f"- Secondary accuracy: **{report['secondaryColorAccuracy']:.0%}**",
        f"- Multi-colour accuracy: **{report['multiColorDetectionAccuracy']:.0%}**",
        f"- Precision: **{report['colorDetectionPrecision']:.0%}**",
        f"- Recall: **{report['colorDetectionRecall']:.0%}**",
        "",
        "| Case | Actual | Predicted | Primary | Secondary |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        actual = ", ".join(row["actual"]["primary"])
        if row["actual"]["secondary"]:
            actual += " + " + ", ".join(row["actual"]["secondary"][:4])
        predicted = row["predicted"]["primary"]
        extra = row["predicted"]["secondary"] + row["predicted"]["accent"]
        if extra:
            predicted += " + " + ", ".join(extra)
        lines.append(
            f"| {row['id']} | {actual} | {predicted} | "
            f"{'ok' if row['primaryOk'] else 'miss'} | "
            f"{'ok' if row['secondaryOk'] else 'miss'} |"
        )
    (REPORTS / "color_error_analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main() -> int:
    report = evaluate()
    print(json.dumps({k: report[k] for k in report if k != "cases"}, indent=2))
    print("wrote", REPORTS / "color_error_analysis.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
