"""Milestone 4.4 dataset audit for Mask R-CNN training preparation.

Inspects converted COCO JSON. Does not repair annotations, train, or touch production.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parent
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from training.annotation_qc import annotation_key, polygon_ok
from training.dataset import BACKGROUND_ID, NUM_FOREGROUND, detection_paths, segmentation_to_mask
from training.label_map import load_label_map
from training.visualize_detection_dataset import PALETTE

DEFAULT_AUDIT_DIR = REPO_ROOT / "outputs" / "maskrcnn_dataset_audit"
TINY_SIDE = 8.0
TINY_AREA = 64.0


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _font() -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", 16)
    except OSError:
        return ImageFont.load_default()


def empty_class_row(class_id: int, name: str) -> dict[str, Any]:
    return {
        "class_id": class_id,
        "class_name": name,
        "num_images": 0,
        "num_annotations": 0,
        "num_boxes": 0,
        "num_masks": 0,
        "pct_annotations": 0.0,
        "min_box_width": None,
        "min_box_height": None,
        "avg_box_width": None,
        "avg_box_height": None,
        "max_box_width": None,
        "max_box_height": None,
        "images_with_invalid": 0,
        "tiny_boxes": 0,
    }


def bbox_issues(bbox: Any, width: int, height: int, tol: float = 1.0) -> list[str]:
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        return ["malformed_bbox"]
    x, y, w, h = (float(v) for v in bbox)
    errors = []
    if w <= 0 or h <= 0:
        errors.append("non_positive_wh")
    if x < -tol or y < -tol or (x + w) > width + tol or (y + h) > height + tol:
        errors.append("bbox_outside_image")
    return errors


def mask_issues(segmentation: Any, width: int, height: int) -> list[str]:
    if segmentation is None:
        return ["missing_segmentation"]
    if isinstance(segmentation, dict):
        size = segmentation.get("size")
        counts = segmentation.get("counts")
        if counts is None or counts == "" or counts == []:
            return ["invalid_rle"]
        if isinstance(size, (list, tuple)) and len(size) == 2:
            if int(size[0]) != height or int(size[1]) != width:
                return ["rle_size_mismatch"]
        return []
    if isinstance(segmentation, list):
        if not segmentation:
            return ["empty_polygon"]
        if not polygon_ok(segmentation, width, height):
            return ["invalid_polygon"]
        return []
    return ["unsupported_segmentation"]


def audit_coco(
    coco: dict[str, Any],
    *,
    image_dir: Path | None,
    split: str,
    approved: list[str],
) -> dict[str, Any]:
    images = coco.get("images") or []
    anns = coco.get("annotations") or []
    cats = coco.get("categories") or []
    id_to_name = {int(c["id"]): str(c["name"]) for c in cats}
    known_ids = set(id_to_name)
    approved_set = set(approved)
    images_by_id = {int(im["id"]): im for im in images}

    class_rows = {name: empty_class_row(i, name) for i, name in enumerate(approved, start=1)}
    class_images: dict[str, set[int]] = {name: set() for name in approved}
    class_invalid_images: dict[str, set[int]] = {name: set() for name in approved}
    widths: dict[str, list[float]] = {name: [] for name in approved}
    heights: dict[str, list[float]] = {name: [] for name in approved}

    errors: Counter[str] = Counter()
    examples: dict[str, list[Any]] = defaultdict(list)

    def note(kind: str, example: Any) -> None:
        errors[kind] += 1
        if len(examples[kind]) < 8:
            examples[kind].append(example)

    extra_names = [n for n in id_to_name.values() if n not in approved_set]
    missing_names = [n for n in approved if n not in set(id_to_name.values())]
    if extra_names:
        note("unexpected_category_names", extra_names)
    if missing_names:
        note("missing_approved_category_names", missing_names)

    image_ids = [int(im["id"]) for im in images]
    if len(image_ids) != len(set(image_ids)):
        note("duplicate_image_ids", split)
    file_names = [Path(str(im.get("file_name") or "")).name for im in images]
    if len(file_names) != len(set(file_names)):
        note("duplicate_file_names_in_split", split)

    anns_by_image: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for ann in anns:
        anns_by_image[int(ann.get("image_id") or -1)].append(ann)

    zero_ann_images = 0
    missing_files = 0
    present_files = 0
    dim_w: list[int] = []
    dim_h: list[int] = []
    for image in images:
        image_id = int(image["id"])
        width, height = int(image.get("width") or 0), int(image.get("height") or 0)
        dim_w.append(width)
        dim_h.append(height)
        if width <= 0 or height <= 0:
            note("invalid_image_size", {"split": split, "image_id": image_id, "size": [width, height]})
        file_name = Path(str(image.get("file_name") or "")).name
        path = (image_dir / file_name) if image_dir is not None else None
        if path is not None:
            if path.is_file():
                present_files += 1
            else:
                missing_files += 1
                note("missing_image_file", {"split": split, "file_name": file_name, "image_id": image_id})
        if not anns_by_image.get(image_id):
            zero_ann_images += 1
            note("image_zero_annotations", {"split": split, "image_id": image_id, "file_name": file_name})

    seen_keys: dict[tuple, int] = {}
    for ann in anns:
        image_id = int(ann.get("image_id") or -1)
        image = images_by_id.get(image_id)
        if image is None:
            note("annotation_unknown_image_id", {"split": split, "ann_id": ann.get("id"), "image_id": image_id})
            continue
        width, height = int(image.get("width") or 0), int(image.get("height") or 0)
        cat_id = int(ann.get("category_id") or 0)
        name = id_to_name.get(cat_id)
        bbox = ann.get("bbox")
        issues = []
        if cat_id not in known_ids or name is None:
            issues.append("unknown_class_id")
            note("unknown_class_id", {"split": split, "ann_id": ann.get("id"), "category_id": cat_id})
        elif name not in approved_set:
            issues.append("unapproved_class")
            note("unapproved_class", {"split": split, "name": name, "category_id": cat_id})
        box_errs = bbox_issues(bbox, width, height)
        issues.extend(box_errs)
        for err in box_errs:
            note(err, {"split": split, "ann_id": ann.get("id"), "bbox": bbox, "image_id": image_id})
        mask_errs = mask_issues(ann.get("segmentation"), width, height)
        issues.extend(mask_errs)
        for err in mask_errs:
            note(err, {"split": split, "ann_id": ann.get("id"), "image_id": image_id})
        if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            key = annotation_key(image_id, cat_id, [float(v) for v in bbox])
            if key in seen_keys:
                note("duplicate_annotation", {"split": split, "ann_id": ann.get("id"), "other": seen_keys[key]})
            else:
                seen_keys[key] = int(ann.get("id") or -1)
        if name in class_rows:
            row = class_rows[name]
            row["num_annotations"] += 1
            class_images[name].add(image_id)
            if issues:
                class_invalid_images[name].add(image_id)
            if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
                _x, _y, w, h = (float(v) for v in bbox)
                row["num_boxes"] += 1
                widths[name].append(w)
                heights[name].append(h)
                if w < TINY_SIDE or h < TINY_SIDE or (w * h) < TINY_AREA:
                    row["tiny_boxes"] += 1
            if ann.get("segmentation") is not None:
                row["num_masks"] += 1

    total_anns = len(anns)
    for name, row in class_rows.items():
        row["num_images"] = len(class_images[name])
        row["images_with_invalid"] = len(class_invalid_images[name])
        row["pct_annotations"] = (100.0 * row["num_annotations"] / total_anns) if total_anns else 0.0
        if widths[name]:
            row["min_box_width"] = min(widths[name])
            row["max_box_width"] = max(widths[name])
            row["avg_box_width"] = sum(widths[name]) / len(widths[name])
            row["min_box_height"] = min(heights[name])
            row["max_box_height"] = max(heights[name])
            row["avg_box_height"] = sum(heights[name]) / len(heights[name])

    return {
        "split": split,
        "total_images": len(images),
        "total_annotations": total_anns,
        "total_classes_in_json": len(cats),
        "images_with_zero_annotations": zero_ann_images,
        "image_files_present": present_files,
        "image_files_missing": missing_files,
        "file_names": file_names,
        "image_ids": image_ids,
        "class_rows": class_rows,
        "errors": dict(errors),
        "examples": {k: v for k, v in examples.items()},
        "image_width": {"min": min(dim_w) if dim_w else None, "max": max(dim_w) if dim_w else None, "avg": (sum(dim_w) / len(dim_w) if dim_w else None)},
        "image_height": {"min": min(dim_h) if dim_h else None, "max": max(dim_h) if dim_h else None, "avg": (sum(dim_h) / len(dim_h) if dim_h else None)},
        "approved": list(approved),
        "background_id": BACKGROUND_ID,
    }


def compare_splits(split_audits: dict[str, dict[str, Any]]) -> dict[str, Any]:
    names = {
        split: set(payload["file_names"])
        for split, payload in split_audits.items()
    }
    ids = {
        split: set(payload["image_ids"])
        for split, payload in split_audits.items()
    }
    overlaps = {}
    if "train" in names and "val" in names:
        overlaps["train_val_filename"] = sorted(names["train"] & names["val"])
        overlaps["train_val_image_id"] = sorted(ids["train"] & ids["val"])
    if "train" in names and "test" in names:
        overlaps["train_test_filename"] = sorted(names["train"] & names["test"])
        overlaps["train_test_image_id"] = sorted(ids["train"] & ids["test"])
    if "val" in names and "test" in names:
        overlaps["val_test_filename"] = sorted(names["val"] & names["test"])
        overlaps["val_test_image_id"] = sorted(ids["val"] & ids["test"])

    class_presence = {}
    for split, payload in split_audits.items():
        class_presence[split] = {
            name: row["num_annotations"] for name, row in payload["class_rows"].items()
        }
    missing = {}
    if "train" in class_presence and "val" in class_presence:
        missing["in_train_not_val"] = [
            n for n, c in class_presence["train"].items() if c > 0 and class_presence["val"].get(n, 0) == 0
        ]
        missing["in_val_not_train"] = [
            n for n, c in class_presence["val"].items() if c > 0 and class_presence["train"].get(n, 0) == 0
        ]
    return {
        "filename_and_id_overlaps": {k: v for k, v in overlaps.items()},
        "overlap_counts": {k: len(v) for k, v in overlaps.items()},
        "class_presence": class_presence,
        "class_gaps": missing,
    }


def classify_imbalance(class_rows: dict[str, dict[str, Any]]) -> dict[str, Any]:
    counts = {name: row["num_annotations"] for name, row in class_rows.items()}
    values = list(counts.values())
    total = sum(values) or 1
    mean = sum(values) / len(values)
    high, medium, low, scarce = [], [], [], []
    for name, count in counts.items():
        pct = 100.0 * count / total
        if count == 0 or pct < 1.0:
            scarce.append(name)
            low.append(name)
        elif count >= 2 * mean:
            high.append(name)
        elif count <= 0.5 * mean:
            low.append(name)
        else:
            medium.append(name)
    ratio = (max(values) / max(min(v for v in values if v > 0), 1)) if any(values) else 0.0
    return {
        "mean_annotations": mean,
        "max_min_ratio": ratio,
        "high_frequency": high,
        "medium_frequency": medium,
        "low_frequency": low,
        "suspiciously_few": scarce,
        "counts": counts,
    }


def sample_image_mask_quality(
    coco: dict[str, Any],
    image_dir: Path,
    approved: list[str],
    per_class: int = 2,
) -> dict[str, Any]:
    cats = {int(c["id"]): str(c["name"]) for c in coco.get("categories") or []}
    images_by_id = {int(im["id"]): im for im in coco.get("images") or []}
    by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ann in coco.get("annotations") or []:
        name = cats.get(int(ann.get("category_id") or 0))
        if name in approved and len(by_class[name]) < per_class * 4:
            by_class[name].append(ann)
    modes: Counter[str] = Counter()
    failures: list[str] = []
    mismatches = 0
    checked = 0
    mask_shape_mismatch = 0
    bbox_mask_loose = 0
    for name in approved:
        for ann in by_class[name][:per_class]:
            image = images_by_id.get(int(ann["image_id"]))
            if image is None:
                continue
            path = image_dir / Path(str(image.get("file_name") or "")).name
            checked += 1
            if not path.is_file():
                failures.append(f"missing {path.name}")
                continue
            try:
                with Image.open(path) as im:
                    modes[str(im.mode)] += 1
                    rgb = ImageOps.exif_transpose(im).convert("RGB")
                    w, h = rgb.size
            except Exception as exc:
                failures.append(f"{path.name}: {type(exc).__name__}: {exc}")
                continue
            if w != int(image["width"]) or h != int(image["height"]):
                mismatches += 1
            try:
                mask = segmentation_to_mask(ann.get("segmentation"), h, w)
            except Exception as exc:
                failures.append(f"mask {path.name} ann {ann.get('id')}: {exc}")
                continue
            if mask.shape != (h, w):
                mask_shape_mismatch += 1
            if isinstance(ann.get("bbox"), (list, tuple)) and len(ann["bbox"]) == 4:
                x, y, bw, bh = (float(v) for v in ann["bbox"])
                coords = np.argwhere(mask > 0)
                if coords.size:
                    my1, mx1 = (int(v) for v in coords.min(axis=0))
                    my2, mx2 = (int(v) for v in coords.max(axis=0))
                    if mx2 < x - 8 or my2 < y - 8 or mx1 > x + bw + 8 or my1 > y + bh + 8:
                        bbox_mask_loose += 1
    return {
        "samples_checked": checked,
        "pil_modes": dict(modes),
        "load_failures": failures[:20],
        "json_vs_file_size_mismatch": mismatches,
        "mask_shape_mismatch": mask_shape_mismatch,
        "bbox_mask_disjoint": bbox_mask_loose,
    }


def write_class_previews(
    coco: dict[str, Any],
    image_dir: Path,
    dest_dir: Path,
    approved: list[str],
    per_class: int = 3,
) -> list[str]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    cats = {int(c["id"]): str(c["name"]) for c in coco.get("categories") or []}
    images_by_id = {int(im["id"]): im for im in coco.get("images") or []}
    anns_by_image: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for ann in coco.get("annotations") or []:
        anns_by_image[int(ann["image_id"])].append(ann)
    chosen: dict[str, list[int]] = {name: [] for name in approved}
    written = []
    for image in coco.get("images") or []:
        image_id = int(image["id"])
        names = [cats.get(int(a["category_id"])) for a in anns_by_image.get(image_id, [])]
        path = image_dir / Path(str(image.get("file_name") or "")).name
        if not path.is_file():
            continue
        for name in approved:
            if name in names and len(chosen[name]) < per_class and image_id not in chosen[name]:
                dest = dest_dir / f"{name}_{len(chosen[name]):02d}_{path.stem}.jpg"
                _draw_gt(path, anns_by_image[image_id], cats, dest)
                chosen[name].append(image_id)
                written.append(str(dest))
        if all(len(v) >= per_class for v in chosen.values()):
            break
    return written


def _draw_gt(path: Path, anns: list[dict[str, Any]], cats: dict[int, str], dest: Path) -> None:
    with Image.open(path) as im:
        rgb = ImageOps.exif_transpose(im).convert("RGBA")
    overlay = Image.new("RGBA", rgb.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(rgb)
    font = _font()
    mask_rgba = np.zeros((rgb.size[1], rgb.size[0], 4), dtype=np.uint8)
    for ann in anns:
        name = cats.get(int(ann.get("category_id") or 0), "unknown")
        color = PALETTE.get(name, (255, 255, 255))
        bbox = ann.get("bbox") or [0, 0, 0, 0]
        x, y, w, h = (float(v) for v in bbox)
        draw.rectangle([x, y, x + w, y + h], outline=color, width=3)
        draw.text((x + 2, max(0.0, y - 18.0)), name, fill=color, font=font)
        try:
            mask = segmentation_to_mask(ann.get("segmentation"), rgb.size[1], rgb.size[0])
            instance = mask > 0
            mask_rgba[instance, 0] = color[0]
            mask_rgba[instance, 1] = color[1]
            mask_rgba[instance, 2] = color[2]
            mask_rgba[instance, 3] = np.maximum(mask_rgba[instance, 3], 90)
        except Exception:
            continue
    out = Image.alpha_composite(rgb, Image.fromarray(mask_rgba, mode="RGBA")).convert("RGB")
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.save(dest, quality=92)


def load_split(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def recommended_experiment(combined_rows: dict[str, dict[str, Any]], cpu: bool = True) -> dict[str, Any]:
    return {
        "max_train_images": 500 if cpu else 2000,
        "max_val_images": 100 if cpu else 300,
        "epochs": 3 if cpu else 8,
        "batch_size": 1 if cpu else 2,
        "num_workers": 0 if cpu else 2,
        "learning_rate": 0.005,
        "min_size": 256 if cpu else 800,
        "max_size": 320 if cpu else 1333,
        "subset_mode": "class_aware",
        "seed": 42,
        "score_threshold_eval": 0.3,
        "device": "cpu" if cpu else "auto",
        "selection": (
            "Scan every train/val image that has a file on disk, group by the 15 detector "
            "classes, shuffle each group with seed 42, then greedily round-robin from the "
            "rarest class so a 500-image CPU subset still contains shirt/skirt/bag/hat/belt/"
            "accessories rather than the first 500 JSON rows (which over-represent shoes/dress)."
        ),
        "do_not_run_now": True,
        "allow_full": False,
    }


def render_audit_markdown(payload: dict[str, Any]) -> str:
    mapping = payload["class_mapping"]
    lines = [
        "# Mask R-CNN dataset audit",
        "",
        f"Generated: {payload['generated_at']}",
        "",
        "Does not train. Does not modify production inference. Does not change the 15-class taxonomy.",
        "",
        "## Class mapping",
        "",
        f"- background: `{payload['background_id']}`",
    ]
    for item in mapping:
        lines.append(f"- `{item['class_id']}` → `{item['class_name']}`")
    lines += ["", "## Totals", ""]
    totals = payload["totals"]
    lines.append(f"- images: {totals['images']}")
    lines.append(f"- annotations: {totals['annotations']}")
    lines.append(f"- classes found: {totals['classes_found']}")
    lines.append("")
    lines += ["## Per-class statistics", "", "| id | class | images | anns | boxes | masks | % | min W×H | avg W×H | max W×H | invalid-image count | tiny boxes |", "|---:|---|---:|---:|---:|---:|---:|---|---|---|---:|---:|"]
    for row in payload["per_class"]:
        min_wh = "—" if row["min_box_width"] is None else f"{row['min_box_width']:.1f}×{row['min_box_height']:.1f}"
        avg_wh = "—" if row["avg_box_width"] is None else f"{row['avg_box_width']:.1f}×{row['avg_box_height']:.1f}"
        max_wh = "—" if row["max_box_width"] is None else f"{row['max_box_width']:.1f}×{row['max_box_height']:.1f}"
        lines.append(
            f"| {row['class_id']} | {row['class_name']} | {row['num_images']} | {row['num_annotations']} | "
            f"{row['num_boxes']} | {row['num_masks']} | {row['pct_annotations']:.2f} | {min_wh} | {avg_wh} | {max_wh} | "
            f"{row['images_with_invalid']} | {row['tiny_boxes']} |"
        )
    imb = payload["imbalance"]
    lines += [
        "",
        "## Class imbalance",
        "",
        f"- high-frequency: {', '.join(imb['high_frequency']) or 'none'}",
        f"- medium-frequency: {', '.join(imb['medium_frequency']) or 'none'}",
        f"- low-frequency: {', '.join(imb['low_frequency']) or 'none'}",
        f"- suspiciously few (<1% or zero): {', '.join(imb['suspiciously_few']) or 'none'}",
        f"- max/min annotation ratio: {imb['max_min_ratio']:.1f}",
        "",
        "## Integrity errors (counts)",
        "",
    ]
    for key, value in sorted(payload["integrity_errors"].items()):
        lines.append(f"- `{key}`: {value}")
    split = payload["split_checks"]
    lines += ["", "## Train / validation split", "", f"- overlap counts: `{split['overlap_counts']}`", f"- class gaps: `{split['class_gaps']}`", ""]
    rec = payload["recommended_experiment"]
    lines += [
        "## Recommended next experiment (not launched)",
        "",
        f"- train images: {rec['max_train_images']}",
        f"- val images: {rec['max_val_images']}",
        f"- epochs: {rec['epochs']}",
        f"- subset: `{rec['subset_mode']}`",
        f"- selection: {rec['selection']}",
        "",
    ]
    return "\n".join(lines) + "\n"


def merge_class_rows(split_audits: dict[str, dict[str, Any]], approved: list[str]) -> list[dict[str, Any]]:
    merged = {name: empty_class_row(i, name) for i, name in enumerate(approved, start=1)}
    width_acc: dict[str, list[float]] = {name: [] for name in approved}
    height_acc: dict[str, list[float]] = {name: [] for name in approved}
    images: dict[str, int] = {name: 0 for name in approved}
    for payload in split_audits.values():
        for name, row in payload["class_rows"].items():
            dest = merged[name]
            dest["num_annotations"] += row["num_annotations"]
            dest["num_boxes"] += row["num_boxes"]
            dest["num_masks"] += row["num_masks"]
            dest["images_with_invalid"] += row["images_with_invalid"]
            dest["tiny_boxes"] += row["tiny_boxes"]
            images[name] += row["num_images"]
            if row["min_box_width"] is not None:
                width_acc[name].extend([row["min_box_width"], row["max_box_width"], row["avg_box_width"]])
            if row["avg_box_width"] is not None:
                # Reconstruct averages only from min/max is wrong. Store from per-split avg weighted by boxes.
                pass
    # Weighted average from splits
    for name in approved:
        box_sum_w = 0.0
        box_sum_h = 0.0
        box_n = 0
        min_w = min_h = None
        max_w = max_h = None
        for payload in split_audits.values():
            row = payload["class_rows"][name]
            n = row["num_boxes"]
            if n and row["avg_box_width"] is not None:
                box_sum_w += row["avg_box_width"] * n
                box_sum_h += row["avg_box_height"] * n
                box_n += n
            if row["min_box_width"] is not None:
                min_w = row["min_box_width"] if min_w is None else min(min_w, row["min_box_width"])
                min_h = row["min_box_height"] if min_h is None else min(min_h, row["min_box_height"])
                max_w = row["max_box_width"] if max_w is None else max(max_w, row["max_box_width"])
                max_h = row["max_box_height"] if max_h is None else max(max_h, row["max_box_height"])
        dest = merged[name]
        dest["num_images"] = images[name]
        dest["pct_annotations"] = 0.0
        dest["min_box_width"] = min_w
        dest["min_box_height"] = min_h
        dest["max_box_width"] = max_w
        dest["max_box_height"] = max_h
        dest["avg_box_width"] = (box_sum_w / box_n) if box_n else None
        dest["avg_box_height"] = (box_sum_h / box_n) if box_n else None
    total = sum(r["num_annotations"] for r in merged.values()) or 1
    for row in merged.values():
        row["pct_annotations"] = 100.0 * row["num_annotations"] / total
    return [merged[name] for name in approved]


def run_audit(
    output_dir: Path,
    *,
    previews_per_class: int = 3,
    write_previews: bool = True,
) -> dict[str, Any]:
    mapping = load_label_map()
    approved = list(mapping.detector_classes)
    paths = detection_paths()
    split_audits = {}
    quality = {}
    preview_files: list[str] = []
    for split in ("train", "val", "test"):
        coco = load_split(paths[f"{split}_ann"])
        split_audits[split] = audit_coco(
            coco,
            image_dir=paths[f"{split}_images"],
            split=split,
            approved=approved,
        )
        quality[split] = sample_image_mask_quality(
            coco,
            paths[f"{split}_images"],
            approved,
            per_class=2 if split == "train" else 1,
        )
        if write_previews and split == "train":
            preview_files = write_class_previews(
                coco,
                paths[f"{split}_images"],
                output_dir / "annotations",
                approved,
                per_class=previews_per_class,
            )
        del coco
    per_class = merge_class_rows(split_audits, approved)
    integrity = Counter()
    for payload in split_audits.values():
        integrity.update(payload["errors"])
    totals = {
        "images": sum(p["total_images"] for p in split_audits.values()),
        "annotations": sum(p["total_annotations"] for p in split_audits.values()),
        "classes_found": NUM_FOREGROUND,
        "images_with_zero_annotations": sum(p["images_with_zero_annotations"] for p in split_audits.values()),
        "image_files_present": sum(p["image_files_present"] for p in split_audits.values()),
        "image_files_missing": sum(p["image_files_missing"] for p in split_audits.values()),
        "by_split": {
            split: {
                "images": p["total_images"],
                "annotations": p["total_annotations"],
                "files_present": p["image_files_present"],
                "files_missing": p["image_files_missing"],
                "zero_ann_images": p["images_with_zero_annotations"],
                "width": p["image_width"],
                "height": p["image_height"],
            }
            for split, p in split_audits.items()
        },
    }
    payload = {
        "generated_at": _utc_now(),
        "background_id": BACKGROUND_ID,
        "class_mapping": [{"class_id": i, "class_name": n} for i, n in enumerate(approved, start=1)],
        "totals": totals,
        "per_class": per_class,
        "imbalance": classify_imbalance({row["class_name"]: row for row in per_class}),
        "integrity_errors": dict(integrity),
        "split_checks": compare_splits(split_audits),
        "image_mask_quality": quality,
        "preview_files": preview_files,
        "recommended_experiment": recommended_experiment({row["class_name"]: row for row in per_class}, cpu=True),
        "split_error_examples": {split: p["examples"] for split, p in split_audits.items()},
    }
    # Drop huge filename lists from serialized split audits
    serializable_splits = {}
    for split, p in split_audits.items():
        serializable_splits[split] = {
            k: v for k, v in p.items() if k not in {"file_names", "image_ids"}
        }
        serializable_splits[split]["class_rows"] = list(p["class_rows"].values())
    payload["splits"] = serializable_splits
    return payload


def write_outputs(payload: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "dataset_audit.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    fieldnames = [
        "class_id",
        "class_name",
        "num_images",
        "num_annotations",
        "num_boxes",
        "num_masks",
        "pct_annotations",
        "min_box_width",
        "min_box_height",
        "avg_box_width",
        "avg_box_height",
        "max_box_width",
        "max_box_height",
        "images_with_invalid",
        "tiny_boxes",
    ]
    with (output_dir / "dataset_audit.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in payload["per_class"]:
            writer.writerow({k: row.get(k) for k in fieldnames})
    (output_dir / "DATASET_AUDIT_REPORT.md").write_text(render_audit_markdown(payload), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit the converted clothing detection COCO set")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_AUDIT_DIR)
    parser.add_argument("--previews-per-class", type=int, default=3)
    parser.add_argument("--no-previews", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    print("Auditing converted COCO clothing detection set (no training)...")
    payload = run_audit(
        args.output_dir,
        previews_per_class=args.previews_per_class,
        write_previews=not args.no_previews,
    )
    write_outputs(payload, args.output_dir)
    print(f"images: {payload['totals']['images']}")
    print(f"annotations: {payload['totals']['annotations']}")
    print(f"missing files: {payload['totals']['image_files_missing']}")
    print("per-class annotations:")
    for row in payload["per_class"]:
        print(f"  {row['class_id']:2d} {row['class_name']:<12} images={row['num_images']:<6} anns={row['num_annotations']}")
    print(f"wrote {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
