"""Audit and optional flat export of the 4-class garment dataset."""

from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from pathlib import Path

from .config import (
    CLASS_ORDER,
    DEFAULT_DATASET,
    EXTS,
    MODELS_DIR,
    SOURCE_FOLDERS,
)


def collect_split(root: Path, split: str) -> list[tuple[Path, str]]:
    base = root / split / split
    rows: list[tuple[Path, str]] = []
    if not base.is_dir():
        return rows
    for family, leaf, label in SOURCE_FOLDERS:
        folder = base / family / leaf
        if not folder.is_dir():
            continue
        for path in folder.rglob("*"):
            if path.is_file() and path.suffix.lower() in EXTS:
                rows.append((path, label))
    return rows


def audit(root: Path) -> dict:
    report: dict = {
        "root": str(root),
        "classes": list(CLASS_ORDER),
        "splits": {},
        "imbalance": {},
        "issues": [],
        "notes": [
            "pants and formal trousers are merged into class 'pants'.",
            "zip and pullover hoodies map to 'jacket' when under jacket/hoodie folders.",
        ],
    }
    for split in ("train", "val", "test"):
        rows = collect_split(root, split)
        counts = Counter(label for _, label in rows)
        report["splits"][split] = {
            "images": len(rows),
            "per_class": {name: int(counts.get(name, 0)) for name in CLASS_ORDER},
        }
        missing = [name for name in CLASS_ORDER if counts.get(name, 0) == 0]
        if missing:
            report["issues"].append(f"{split}: missing classes {missing}")

    train = report["splits"].get("train", {}).get("per_class", {})
    if train and max(train.values()) > 0:
        peak = max(train.values())
        report["imbalance"] = {
            name: {
                "count": train[name],
                "ratio_to_largest": round(train[name] / peak, 3) if peak else 0.0,
            }
            for name in CLASS_ORDER
        }
        low = [n for n, c in train.items() if c < peak * 0.35]
        if low:
            report["issues"].append(
                f"Train classes under 35% of largest class (use class weights): {low}"
            )
    else:
        report["issues"].append(f"No training images under {root}")
    return report


def export_flat(root: Path, out: Path, *, copy_files: bool = False) -> dict:
    """Write train/val/test/{class}/ trees (symlink when possible, else copy)."""
    summary: dict = {"out": str(out), "copied": copy_files, "counts": {}}
    for split in ("train", "val", "test"):
        rows = collect_split(root, split)
        summary["counts"][split] = Counter()
        for src, label in rows:
            dest_dir = out / split / label
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / src.name
            if dest.exists():
                dest = dest_dir / f"{src.stem}_{abs(hash(str(src))) % 10_000_000}{src.suffix}"
            if copy_files:
                shutil.copy2(src, dest)
            else:
                try:
                    if dest.exists() or dest.is_symlink():
                        dest.unlink()
                    dest.symlink_to(src.resolve())
                except OSError:
                    shutil.copy2(src, dest)
            summary["counts"][split][label] += 1
        summary["counts"][split] = dict(summary["counts"][split])
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit / export 4-class garment data")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument(
        "--export-dir",
        type=Path,
        default=None,
        help="Optional flat ImageFolder export root",
    )
    parser.add_argument("--copy", action="store_true", help="Copy instead of symlink")
    args = parser.parse_args()

    report = audit(args.dataset)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    audit_path = MODELS_DIR / "garment4_dataset_audit.json"
    audit_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Wrote {audit_path}")

    if args.export_dir is not None and not args.audit_only:
        summary = export_flat(args.dataset, args.export_dir, copy_files=args.copy)
        print(json.dumps(summary, indent=2))
    return 0 if not report["issues"] or all(
        "missing classes" not in i for i in report["issues"]
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
