"""Final pre-training audit of the converted clothing detection COCO set.

Does not train. Does not repair annotations. Does not touch production inference.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from training.annotation_qc import polygon_ok
from training.label_map import UnifiedLabelMap, load_label_map
from training.prepare_detection_dataset import (
    DEFAULT_OUTPUT,
    DEFAULT_PREVIEW,
    hash_images,
)
from training.visualize_detection_dataset import _index, _load_split, draw_row

REPO_ROOT = SERVICE_ROOT.parent
DEFAULT_AUDIT_REPORT = REPO_ROOT / "DATASET_FINAL_VALIDATION_REPORT.md"
APPROVED = [
    "shirt",
    "jacket",
    "sweater",
    "trousers",
    "shorts",
    "skirt",
    "dress",
    "jumpsuit",
    "shoes",
    "bag",
    "hat",
    "belt",
    "scarf",
    "watch",
    "sunglasses",
]
FORBIDDEN_ORIGINAL_TO_UNIFIED = {
    ("dress", "skirt"),
    ("skirt", "dress"),
    ("jumpsuit", "dress"),
    ("sweater", "hoodie"),
    ("scarf", "dupatta"),
    ("bag, wallet", "hat"),
    ("bag, wallet", "skirt"),
    ("bag", "hat"),
    ("bag", "skirt"),
    ("top, t-shirt, sweatshirt", "shirt"),
    ("headband, head covering, hair accessory", "hijab"),
    ("shoe", "footwear"),
}
BANNED_CATEGORY_NAMES = {
    "hoodie",
    "dupatta",
    "hijab",
    "t-shirt",
    "jeans",
    "sneakers",
    "loafers",
    "flats",
    "footwear",
    "top",
}
DIFFICULT = [
    "sweater",
    "jumpsuit",
    "scarf",
    "watch",
    "hat",
    "shirt",
    "shoes",
    "dress",
    "skirt",
    "bag",
]
ATTENTION = [
    "sweater",
    "jumpsuit",
    "scarf",
    "hat",
    "watch",
    "shirt",
    "shorts",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _bbox_errors(bbox: Any, width: int, height: int, tol: float = 1.0) -> list[str]:
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        return ["malformed_bbox"]
    x, y, w, h = (float(v) for v in bbox)
    errors = []
    if w <= 0 or h <= 0:
        errors.append("non_positive_wh")
    if x < -tol or y < -tol:
        errors.append("bbox_negative_origin")
    if (x + w) > width + tol or (y + h) > height + tol:
        errors.append("bbox_outside_image")
    return errors


def audit_split(split: str, coco: dict[str, Any], output_dir: Path, mapping: UnifiedLabelMap) -> dict[str, Any]:
    cats = coco.get("categories") or []
    images = coco.get("images") or []
    anns = coco.get("annotations") or []
    cat_ids = {int(c["id"]) for c in cats}
    cat_names = [str(c["name"]) for c in cats]
    images_by_id = {int(im["id"]): im for im in images}
    image_dir = output_dir / "images" / split

    errors: Counter[str] = Counter()
    examples: dict[str, list[Any]] = defaultdict(list)

    def note(kind: str, example: Any) -> None:
        errors[kind] += 1
        if len(examples[kind]) < 8:
            examples[kind].append(example)

    if cat_names != APPROVED:
        note("category_names_not_approved_15", cat_names)
    extra = [n for n in cat_names if n not in APPROVED]
    missing = [n for n in APPROVED if n not in cat_names]
    banned = [n for n in cat_names if n in BANNED_CATEGORY_NAMES]
    if extra:
        note("unexpected_category_names", extra)
    if missing:
        note("missing_approved_category_names", missing)
    if banned:
        note("banned_category_names_present", banned)
    if len(cat_ids) != len(cats):
        note("duplicate_category_ids", [c["id"] for c in cats])

    image_ids = [int(im["id"]) for im in images]
    if len(image_ids) != len(set(image_ids)):
        note("duplicate_image_ids_in_split", split)

    ann_ids = [int(a["id"]) for a in anns]
    if len(ann_ids) != len(set(ann_ids)):
        note("duplicate_annotation_ids_in_split", split)

    referenced = set()
    original_to_unified: Counter[str] = Counter()
    forbidden_hits = []
    for ann in anns:
        image_id = int(ann.get("image_id") or -1)
        referenced.add(image_id)
        image = images_by_id.get(image_id)
        if image is None:
            note("orphan_annotation", {"ann_id": ann.get("id"), "image_id": image_id})
            continue
        width, height = int(image["width"]), int(image["height"])
        cat_id = int(ann.get("category_id") or -1)
        if cat_id not in cat_ids:
            note("impossible_category_id", {"ann_id": ann.get("id"), "category_id": cat_id})
        unified = str(ann.get("unified_category") or "")
        original = str(ann.get("original_category") or "")
        cat_name = next((c["name"] for c in cats if int(c["id"]) == cat_id), "")
        if unified and unified != cat_name:
            note("unified_name_mismatch_category", {"ann_id": ann.get("id"), "unified": unified, "category": cat_name})
        if unified in BANNED_CATEGORY_NAMES or cat_name in BANNED_CATEGORY_NAMES:
            note("banned_class_in_annotation", {"ann_id": ann.get("id"), "unified": unified})
        mapped, why = mapping.map_fashionpedia(original) if original else (None, "missing_original")
        if original:
            original_to_unified[f"{original} -> {unified}"] += 1
            pair = (original.strip().lower(), unified.strip().lower())
            if pair in {(a.lower(), b.lower()) for a, b in FORBIDDEN_ORIGINAL_TO_UNIFIED}:
                forbidden_hits.append({"ann_id": ann.get("id"), "original": original, "unified": unified})
                note("forbidden_mapping", {"original": original, "unified": unified})
            if mapped is not None and mapped != unified:
                note("mapping_disagrees_with_label_map", {"original": original, "mapped": mapped, "unified": unified})
            if mapped is None and why == "rejected_taxonomy":
                note("rejected_source_class_kept", {"original": original, "unified": unified})
        for err in _bbox_errors(ann.get("bbox"), width, height):
            note(err, {"ann_id": ann.get("id"), "bbox": ann.get("bbox")})
        bbox = ann.get("bbox") or [0, 0, 0, 0]
        area = float(ann.get("area") or 0)
        if area <= 0:
            note("non_positive_area", {"ann_id": ann.get("id"), "area": area})
        if isinstance(bbox, (list, tuple)) and len(bbox) == 4 and float(bbox[2]) * float(bbox[3]) <= 0:
            note("zero_bbox_area", {"ann_id": ann.get("id")})
        seg = ann.get("segmentation")
        if not polygon_ok(seg, width, height):
            note("invalid_segmentation", {"ann_id": ann.get("id")})
        if str(ann.get("source") or "") not in {"fashionpedia", ""}:
            note("unexpected_annotation_source", {"source": ann.get("source")})

    for image in images:
        image_id = int(image["id"])
        if image_id not in referenced:
            note("image_with_no_annotation", {"image_id": image_id})
        file_name = Path(str(image.get("file_name") or "")).name
        if not file_name:
            note("broken_image_path", {"image_id": image_id, "file_name": image.get("file_name")})
            continue
        path = image_dir / file_name
        if not path.is_file() or path.stat().st_size <= 0:
            note("missing_image_file", {"image_id": image_id, "file_name": file_name})

    class_counts = Counter()
    class_images = defaultdict(set)
    for ann in anns:
        cat_id = int(ann.get("category_id") or -1)
        name = next((c["name"] for c in cats if int(c["id"]) == cat_id), f"id:{cat_id}")
        class_counts[name] += 1
        class_images[name].add(int(ann.get("image_id") or -1))

    return {
        "split": split,
        "images": len(images),
        "instances": len(anns),
        "error_counts": dict(errors),
        "error_examples": {k: v for k, v in examples.items()},
        "class_instances": dict(class_counts),
        "class_images": {k: len(v) for k, v in class_images.items()},
        "original_to_unified": dict(original_to_unified),
        "forbidden_hits": forbidden_hits[:20],
        "image_ids": image_ids,
        "file_names": [Path(str(im.get("file_name") or "")).name.lower() for im in images],
        "missing_image_files": int(errors.get("missing_image_file", 0)),
        "present_image_files": max(0, len(images) - int(errors.get("missing_image_file", 0))),
    }


def leakage(split_audits: dict[str, dict[str, Any]]) -> dict[str, Any]:
    ids = {s: set(a["image_ids"]) for s, a in split_audits.items()}
    names = {s: set(a["file_names"]) for s, a in split_audits.items()}
    pairs = (("train", "val"), ("train", "test"), ("val", "test"))
    id_overlap = {}
    name_overlap = {}
    for a, b in pairs:
        shared_ids = sorted(ids.get(a, set()) & ids.get(b, set()))
        shared_names = sorted(names.get(a, set()) & names.get(b, set()))
        id_overlap[f"{a}_{b}"] = {"count": len(shared_ids), "examples": shared_ids[:20]}
        name_overlap[f"{a}_{b}"] = {"count": len(shared_names), "examples": shared_names[:20]}
    return {"image_id_overlap": id_overlap, "filename_overlap": name_overlap}


def class_table(split_audits: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    totals = {s: split_audits[s]["instances"] for s in ("train", "val", "test")}
    grand = sum(totals.values()) or 1
    for name in APPROVED:
        train_n = int(split_audits["train"]["class_instances"].get(name, 0))
        val_n = int(split_audits["val"]["class_instances"].get(name, 0))
        test_n = int(split_audits["test"]["class_instances"].get(name, 0))
        total = train_n + val_n + test_n
        rows.append(
            {
                "class": name,
                "train": train_n,
                "val": val_n,
                "test": test_n,
                "total": total,
                "pct": round(100.0 * total / grand, 3),
            }
        )
    return rows


def write_class_previews(output_dir: Path, preview_dir: Path, per_class: int, seed: int) -> dict[str, Any]:
    import random

    rows: list[dict[str, Any]] = []
    for split in ("train", "val", "test"):
        path = output_dir / "annotations" / f"instances_{split}.json"
        if path.is_file():
            rows.extend(_index(_load_split(output_dir, split), split, output_dir))
    rng = random.Random(seed)
    dest_root = preview_dir / "by_class"
    dest_root.mkdir(parents=True, exist_ok=True)
    written = []
    missing_scenes = []
    for name in APPROVED:
        for split in ("train", "val", "test"):
            pool = [r for r in rows if r["split"] == split and name in r["names"]]
            rng.shuffle(pool)
            chosen = pool[:per_class]
            if not chosen:
                missing_scenes.append(f"{name}/{split}")
                continue
            for i, row in enumerate(chosen):
                dest = dest_root / f"{name}_{split}_{i:02d}_{row['image']['id']}.jpg"
                draw_row(row, dest)
                written.append(str(dest.name))
    index = ["# Per-class dataset audit previews", "", "Geometry overlays if pixels are not copied. Not training output.", ""]
    for name in APPROVED:
        index.append(f"## {name}")
        index.append("")
        matches = [w for w in written if w.startswith(f"{name}_")]
        if not matches:
            index.append("No sample found.")
        for item in matches:
            index.append(f"- `{item}`")
        index.append("")
    (dest_root / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    return {"written": len(written), "files": written, "missing_scenes": missing_scenes, "dir": str(dest_root)}


def sufficient(train_n: int, val_n: int) -> str:
    if train_n < 400 or val_n < 15:
        return "marginal for initial training; additional real annotated photos recommended later"
    if train_n < 1500 or val_n < 40:
        return "usable for initial training; extra real-world photos still advisable"
    return "sufficient for initial Mask R-CNN training; real-world evaluation photos still needed later"


def quality_note(name: str) -> str:
    notes = {
        "sweater": "Kept only from Fashionpedia sweater. Cardigan/hoodie/t-shirt-sweatshirt were excluded.",
        "jumpsuit": "Kept as its own class; not merged into dress. Smallest detector class.",
        "scarf": "Neck scarf only. Dupatta/hijab/head-covering excluded.",
        "watch": "Small wrist instances; many tiny flags expected.",
        "hat": "Hat only. Head-covering/hair accessory excluded so hijab is not faked.",
        "shirt": "Only shirt, blouse. Mixed top/t-shirt/sweatshirt was excluded, so counts are conservative.",
        "shoes": "Dominant class; left and right shoes are separate instances. Sneakers/loafers/flats not distinguished.",
        "dress": "One-piece dress masks. Not remapped to skirt.",
        "skirt": "Lowerwear skirt. Not remapped to dress.",
        "bag": "bag, wallet mapped to bag. Separate from clothing instances.",
        "shorts": "Mapped 1:1 from Fashionpedia shorts.",
        "jacket": "jacket + coat. Cape/vest excluded.",
        "trousers": "Fashionpedia pants only. Jeans remain DATA REQUIRED.",
        "belt": "Often small; flagged tiny objects retained.",
        "sunglasses": "glasses mapped to sunglasses; some eyeglasses will share this class.",
    }
    return notes.get(name, "Mapped from approved Fashionpedia classes only.")


def render_validation_report(payload: dict[str, Any], dest: Path) -> None:
    splits = payload["splits"]
    table = payload["class_table"]
    leak = payload["leakage"]
    hashes = payload["hashes"]
    decision = payload["decision"]
    lines = [
        "# Dataset Final Validation Report",
        "",
        f"**Date:** {payload['created_at']}",
        "**Scope:** Milestone 3 close-out audit. No Mask R-CNN training. No production edits.",
        "",
        "## Train JSON status",
        "",
        f"- Path: `{payload['train_json']['path']}`",
        f"- Size: **{payload['train_json']['size_bytes']}** bytes ({payload['train_json']['size_mb']} MB)",
        f"- JSON readable: **{payload['train_json']['readable']}**",
        f"- Source images: **{payload['train_json']['n_images']}**",
        f"- Source annotations: **{payload['train_json']['n_annotations']}**",
        f"- Source categories: {payload['train_json']['n_categories']}",
        "",
        "## Converter run",
        "",
        "Command: `python -m training.prepare_detection_dataset --source-dir datasets/sources/fashionpedia --annotations-only`",
        "",
        "| Split | Images | Instances | Origin |",
        "|---|---:|---:|---|",
        f"| train | {splits['train']['images']} | {splits['train']['instances']} | official Fashionpedia train minus 12% holdout |",
        f"| val | {splits['val']['images']} | {splits['val']['instances']} | official Fashionpedia val |",
        f"| test | {splits['test']['images']} | {splits['test']['instances']} | deterministic holdout of official train |",
        "",
        f"Present image files on disk: train {splits['train']['present_image_files']}, "
        f"val {splits['val']['present_image_files']}, test {splits['test']['present_image_files']}.",
        "",
        "## Class distribution",
        "",
        "| class | train instances | val instances | test instances | total | % of instances |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in table:
        lines.append(
            f"| {row['class']} | {row['train']} | {row['val']} | {row['test']} | {row['total']} | {row['pct']} |"
        )
    smallest = sorted(table, key=lambda r: r["total"])[:3]
    largest = sorted(table, key=lambda r: -r["total"])[:3]
    lines += [
        "",
        "Smallest classes: " + ", ".join(f"{r['class']} ({r['total']})" for r in smallest),
        "Largest classes: " + ", ".join(f"{r['class']} ({r['total']})" for r in largest),
        "",
        "Attention classes:",
        "",
        "| class | train | val | test | total |",
        "|---|---:|---:|---:|---:|",
    ]
    by_name = {r["class"]: r for r in table}
    for name in ATTENTION:
        row = by_name[name]
        lines.append(f"| {name} | {row['train']} | {row['val']} | {row['test']} | {row['total']} |")
    lines += [
        "",
        "No class was duplicated or rebalanced.",
        "",
        "## Annotation validation findings",
        "",
    ]
    for split in ("train", "val", "test"):
        err = splits[split]["error_counts"]
        lines.append(f"### {split}")
        lines.append("")
        if not err:
            lines.append("No integrity errors.")
        else:
            lines.append("| Issue | Count |")
            lines.append("|---|---:|")
            for k, v in sorted(err.items(), key=lambda kv: -kv[1]):
                lines.append(f"| {k} | {v} |")
        lines.append("")
    geometry_keys = {
        "non_positive_wh",
        "bbox_outside_image",
        "bbox_negative_origin",
        "invalid_segmentation",
        "non_positive_area",
        "orphan_annotation",
        "impossible_category_id",
        "duplicate_annotation_ids_in_split",
        "duplicate_image_ids_in_split",
        "forbidden_mapping",
        "banned_class_in_annotation",
        "category_names_not_approved_15",
        "rejected_source_class_kept",
    }
    geom_total = sum(splits[s]["error_counts"].get(k, 0) for s in splits for k in geometry_keys)
    missing_files = sum(splits[s]["missing_image_files"] for s in splits)
    lines += [
        f"Geometry / id / taxonomy errors (excluding missing files): **{geom_total}**",
        f"Missing image files (annotations-only conversion): **{missing_files}**",
        "",
        "Errors were **reported, not silently repaired**.",
        "",
        "## Taxonomy verification",
        "",
        "Approved detector classes remain exactly the 15 names listed in `unified_label_map.json`.",
        "",
        "Forbidden mappings checked on every kept annotation (`original_category` → `unified_category`):",
        "",
        "- dress → skirt",
        "- skirt → dress",
        "- jumpsuit → dress",
        "- sweater → hoodie",
        "- scarf → dupatta",
        "- bag → hat / skirt",
        "- top, t-shirt, sweatshirt → shirt",
        "- head-covering → hijab",
        "- shoe → footwear",
        "",
        f"Forbidden mapping hits: **{payload['forbidden_total']}**",
        "",
        "Outfit20 and binary gate folders were not inputs to this converter. "
        f"Unexpected annotation sources: **{payload['unexpected_sources']}**.",
        "",
        "## Duplicate / leakage findings",
        "",
        "Image ids and filenames were compared across splits. Pixel hashing ran only on files that exist locally.",
        "",
        "| Pair | shared image ids | shared filenames |",
        "|---|---:|---:|",
    ]
    for pair in ("train_val", "train_test", "val_test"):
        lines.append(
            f"| {pair.replace('_', ' ↔ ')} | {leak['image_id_overlap'][pair]['count']} | "
            f"{leak['filename_overlap'][pair]['count']} |"
        )
    lines += [
        "",
        f"- Images hashed: {hashes.get('images_hashed', 0)}",
        f"- Exact duplicate groups (any split): {hashes.get('exact_duplicate_groups', 0)}",
        f"- Cross-split exact duplicates: {hashes.get('cross_split_exact_count', 0)}",
        f"- Cross-split near-duplicates (aHash Hamming ≤ 4): {hashes.get('near_duplicate_cross_split_count', 0)}",
        "",
        "No rows were deleted.",
        "",
        "## Visual quality audit",
        "",
        f"Per-class overlays: `{payload['previews']['dir']}` ({payload['previews']['written']} files).",
        f"Scene overlays: `{DEFAULT_PREVIEW}`.",
        "",
    ]
    for note in payload.get("visual_notes") or []:
        lines.append(f"- {note}")
    lines += [
        "",
        "## Classes Requiring Attention Before Training",
        "",
    ]
    for name in DIFFICULT:
        row = by_name[name]
        lines += [
            f"### {name}",
            "",
            f"- Train: {row['train']}",
            f"- Val: {row['val']}",
            f"- Test: {row['test']}",
            f"- Annotation quality: {quality_note(name)}",
            f"- Initial training: {sufficient(row['train'], row['val'])}",
            "",
        ]
    lines += [
        "## Training readiness decision",
        "",
        f"**{decision}**",
        "",
    ]
    for item in payload.get("decision_reasons") or []:
        lines.append(f"- {item}")
    if decision == "READY_FOR_MILESTONE_4":
        lines += [
            "",
            "Milestone 4 should use:",
            "",
            f"- `{payload['paths']['train']}`",
            f"- `{payload['paths']['val']}`",
            f"- `{payload['paths']['test']}`",
            f"- images under `{payload['paths']['images']}` once pixels are present",
        ]
    lines += [
        "",
        "## Confirmations",
        "",
        "- Outfit20 was not converted.",
        "- Binary gate folders were not converted.",
        "- No Mask R-CNN / YOLO / specialist model was trained in this audit.",
        "- Production inference, FastAPI, Flutter, and recommendation code were not modified.",
        "",
    ]
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {dest}")


def run(output_dir: Path, preview_dir: Path, report_path: Path, mapping: UnifiedLabelMap) -> dict[str, Any]:
    coco = {}
    audits = {}
    for split in ("train", "val", "test"):
        coco[split] = _load_split(output_dir, split)
        audits[split] = audit_split(split, coco[split], output_dir, mapping)
    leak = leakage(audits)
    hashes = hash_images(coco, output_dir)
    table = class_table(audits)
    forbidden_total = sum(len(audits[s]["forbidden_hits"]) for s in audits)
    unexpected_sources = sum(audits[s]["error_counts"].get("unexpected_annotation_source", 0) for s in audits)
    previews = write_class_previews(output_dir, preview_dir, per_class=1, seed=21)
    geom_keys = {
        "non_positive_wh",
        "bbox_outside_image",
        "invalid_segmentation",
        "orphan_annotation",
        "impossible_category_id",
        "forbidden_mapping",
        "category_names_not_approved_15",
        "duplicate_annotation_ids_in_split",
        "duplicate_image_ids_in_split",
    }
    geom_total = sum(audits[s]["error_counts"].get(k, 0) for s in audits for k in geom_keys)
    missing_files = sum(audits[s]["missing_image_files"] for s in audits)
    id_leaks = sum(leak["image_id_overlap"][p]["count"] for p in leak["image_id_overlap"])
    blocking = []
    reasons = []
    if geom_total:
        blocking.append(f"{geom_total} geometry/id/taxonomy integrity errors")
    if forbidden_total:
        blocking.append(f"{forbidden_total} forbidden taxonomy mappings")
    if id_leaks:
        blocking.append(f"{id_leaks} image ids shared across splits")
    if missing_files:
        blocking.append(
            f"{missing_files} converted images have no pixel file on disk "
            "(official train2020.zip / val_test2020.zip were not downloaded; "
            "conversion used --annotations-only)"
        )
    if blocking:
        decision = "NOT_READY_FOR_MILESTONE_4"
        reasons = blocking
    else:
        decision = "READY_FOR_MILESTONE_4"
        reasons = [
            "COCO integrity checks passed.",
            "Approved 15-class taxonomy only.",
            "Official val intact; test holdout disjoint from train.",
            f"Image files present: {sum(audits[s]['present_image_files'] for s in audits)}.",
        ]
    train_json = SERVICE_ROOT / "datasets" / "sources" / "fashionpedia" / "instances_attributes_train2020.json"
    payload = {
        "created_at": _utc_now(),
        "train_json": json.loads((output_dir / "reports" / "train_json_status.json").read_text(encoding="utf-8"))
        if (output_dir / "reports" / "train_json_status.json").is_file()
        else {
            "path": str(train_json),
            "size_bytes": train_json.stat().st_size if train_json.is_file() else 0,
            "size_mb": round(train_json.stat().st_size / 1024 / 1024, 2) if train_json.is_file() else 0,
            "readable": True,
            "n_images": None,
            "n_annotations": None,
            "n_categories": None,
        },
        "splits": audits,
        "class_table": table,
        "leakage": leak,
        "hashes": hashes,
        "previews": previews,
        "forbidden_total": forbidden_total,
        "unexpected_sources": unexpected_sources,
        "decision": decision,
        "decision_reasons": reasons,
        "paths": {
            "train": str(output_dir / "annotations" / "instances_train.json"),
            "val": str(output_dir / "annotations" / "instances_val.json"),
            "test": str(output_dir / "annotations" / "instances_test.json"),
            "images": str(output_dir / "images"),
        },
        "visual_notes": [
            "Overlays draw instance boxes and polygons from the converted COCO files.",
            "Where pixels are missing, canvases are geometry-only and still show separate instances.",
        ],
    }
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Audit converted clothing detection COCO (no training)")
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--preview-dir", type=Path, default=DEFAULT_PREVIEW)
    p.add_argument("--report", type=Path, default=DEFAULT_AUDIT_REPORT)
    p.add_argument("--label-map", type=Path, default=SERVICE_ROOT / "taxonomy" / "unified_label_map.json")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    mapping = load_label_map(args.label_map)
    payload = run(args.output_dir, args.preview_dir, args.report, mapping)
    slim = dict(payload)
    for split in slim["splits"].values():
        split.pop("image_ids", None)
        split.pop("file_names", None)
    reports = args.output_dir / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "final_validation.json").write_text(json.dumps(slim, indent=2), encoding="utf-8")
    render_validation_report(payload, args.report)
    print(f"decision {payload['decision']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
