"""Convert Fashionpedia instance annotations into the Adore 15-class COCO set.

Does not train a model. Does not touch production inference.

Source of truth: ml_service/taxonomy/unified_label_map.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from PIL import Image

from training.annotation_qc import (
    annotation_key,
    average_hash_bytes,
    bbox_was_clipped,
    clip_bbox,
    hamming64,
    is_tiny,
    polygon_ok,
)
from training.label_map import UnifiedLabelMap, load_label_map

REPO_ROOT = SERVICE_ROOT.parent
DEFAULT_MAP = SERVICE_ROOT / "taxonomy" / "unified_label_map.json"
DEFAULT_SOURCE = SERVICE_ROOT / "datasets" / "sources" / "fashionpedia"
DEFAULT_OUTPUT = SERVICE_ROOT / "datasets" / "clothing_detection"
DEFAULT_PREVIEW = REPO_ROOT / "evaluation_results" / "dataset_preview"
DEFAULT_REPORT = REPO_ROOT / "DATASET_PREPARATION_REPORT.md"
DEFAULT_HF_CACHE = SERVICE_ROOT / "datasets" / "sources" / "hf_cache"

FASHIONPEDIA = {
    "name": "Fashionpedia",
    "version": "2020 (CVDF / iFashionist release)",
    "license": "CC BY 4.0",
    "paper": "Jia et al., ECCV 2020",
    "images_expected": 46781,
    "train_images_expected": 45623,
    "val_images_expected": 1158,
    "size_note": "Images ~several GB (train2020.zip + val_test2020.zip); annotation JSON hundreds of MB.",
    "urls": {
        "train_images": "https://s3.amazonaws.com/ifashionist-dataset/images/train2020.zip",
        "val_images": "https://s3.amazonaws.com/ifashionist-dataset/images/val_test2020.zip",
        "train_ann": "https://s3.amazonaws.com/ifashionist-dataset/annotations/instances_attributes_train2020.json",
        "val_ann": "https://s3.amazonaws.com/ifashionist-dataset/annotations/instances_attributes_val2020.json",
    },
}

EXCLUDED_SOURCES = {
    "outfit20": "synthetic full-frame boxes (0.5 0.5 0.92 0.92)",
    "binary_gates": "rivalry other/positive folders, no instance GT",
    "local_adore_folders": "classification labels only",
    "grigorev": "no boxes/masks",
    "hf_fashion_product": "shop crops, no instance GT",
    "secondhand": "background-removed crops, not garment masks",
    "upperwear6_lowerwear5": "derived classification sets",
    "deepfashion2": "academic non-commercial license; form+password required; not on disk; tops are not shirt/t-shirt",
}

HOLDOUT_SALT = "adore-milestone3-fashionpedia-test-holdout"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _download(url: str, dest: Path, min_bytes: int = 1024) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size >= min_bytes:
        print(f"already present {dest} ({dest.stat().st_size} bytes)", flush=True)
        return
    if dest.is_file():
        print(f"incomplete {dest} ({dest.stat().st_size} bytes); resuming", flush=True)
    print(f"downloading {url}", flush=True)
    print(f"  -> {dest}", flush=True)
    curl = "curl.exe" if os.name == "nt" else "curl"
    last_error = None
    for attempt in range(1, 13):
        try:
            subprocess.run(
                [
                    curl,
                    "-L",
                    "--retry",
                    "8",
                    "--retry-delay",
                    "4",
                    "--retry-all-errors",
                    "--speed-limit",
                    "50000",
                    "--speed-time",
                    "45",
                    "-C",
                    "-",
                    "-o",
                    str(dest),
                    url,
                ],
                check=True,
            )
            size = dest.stat().st_size if dest.is_file() else 0
            print(f"saved {dest} ({size} bytes)", flush=True)
            if size >= min_bytes:
                return
            print(f"still short of {min_bytes} bytes; resume attempt {attempt}", flush=True)
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            last_error = exc
            size = dest.stat().st_size if dest.is_file() else 0
            print(f"curl attempt {attempt} failed ({exc}); keeping {size} bytes and retrying", flush=True)
            time.sleep(min(30, 2 * attempt))
    raise RuntimeError(f"download failed for {url} after retries: {last_error}")


def download_fashionpedia(source_dir: Path, images: bool) -> dict[str, Path]:
    source_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "train_ann": source_dir / "instances_attributes_train2020.json",
        "val_ann": source_dir / "instances_attributes_val2020.json",
    }
    _download(FASHIONPEDIA["urls"]["train_ann"], paths["train_ann"], min_bytes=500_000_000)
    _download(FASHIONPEDIA["urls"]["val_ann"], paths["val_ann"], min_bytes=10_000_000)
    if images:
        paths["train_images"] = source_dir / "train2020.zip"
        paths["val_images"] = source_dir / "val_test2020.zip"
        # Official Content-Length: train2020.zip 3344364592; val_test2020.zip 236499034
        _download(FASHIONPEDIA["urls"]["train_images"], paths["train_images"], min_bytes=3_000_000_000)
        _download(FASHIONPEDIA["urls"]["val_images"], paths["val_images"], min_bytes=200_000_000)
    return paths


def _load_coco(path: Path) -> dict[str, Any]:
    print(f"loading {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _category_name_lookup(coco: dict[str, Any]) -> dict[int, str]:
    lookup: dict[int, str] = {}
    for cat in coco.get("categories") or []:
        lookup[int(cat["id"])] = str(cat["name"])
    return lookup


def _holdout_is_test(image_id: int, frac: float) -> bool:
    digest = hashlib.md5(f"{HOLDOUT_SALT}:{image_id}".encode("utf-8")).hexdigest()
    return (int(digest[:8], 16) / 0xFFFFFFFF) < frac


def convert_split(
    coco: dict[str, Any],
    label_map: UnifiedLabelMap,
    split_name: str,
    *,
    min_area: float,
    min_side: float,
    flag_tiny_area: float,
    holdout_frac: float,
    official_split: str,
) -> dict[str, Any]:
    """Convert one official Fashionpedia JSON into mapped records (not yet written)."""
    names = _category_name_lookup(coco)
    images = {int(im["id"]): im for im in coco.get("images") or []}
    buckets: dict[str, dict[str, Any]] = {
        "train": {"images": {}, "annotations": []},
        "val": {"images": {}, "annotations": []},
        "test": {"images": {}, "annotations": []},
    }
    reasons: Counter[str] = Counter()
    source_class_kept: Counter[str] = Counter()
    source_class_dropped: Counter[str] = Counter()
    tiny_flagged: Counter[str] = Counter()
    seen_keys: set[tuple] = set()
    anns_in = len(coco.get("annotations") or [])

    for ann in coco.get("annotations") or []:
        image_id = int(ann.get("image_id", -1))
        image = images.get(image_id)
        if image is None:
            reasons["missing_image_record"] += 1
            continue
        width, height = int(image["width"]), int(image["height"])
        cat_id = ann.get("category_id")
        try:
            original_name = names[int(cat_id)]
        except (KeyError, TypeError, ValueError):
            reasons["impossible_category_id"] += 1
            continue
        unified, why = label_map.map_fashionpedia(original_name)
        if unified is None:
            reasons[why] += 1
            source_class_dropped[original_name] += 1
            continue
        bbox = clip_bbox(list(ann.get("bbox") or []), width, height)
        if bbox is None:
            reasons["invalid_or_zero_bbox"] += 1
            continue
        if bbox_was_clipped(list(ann.get("bbox") or [0, 0, 0, 0]), bbox):
            reasons["bbox_clipped_to_image"] += 1
        if is_tiny(bbox, min_area, min_side):
            reasons["degenerate_tiny_dropped"] += 1
            continue
        if bbox[2] * bbox[3] < flag_tiny_area:
            tiny_flagged[unified] += 1
            reasons["tiny_kept_flagged"] += 1
        seg = ann.get("segmentation")
        if not polygon_ok(seg, width, height):
            reasons["invalid_or_missing_segmentation"] += 1
            continue
        if int(ann.get("iscrowd") or 0) == 1:
            reasons["iscrowd_excluded"] += 1
            continue
        new_cat = label_map.class_id(unified)
        key = annotation_key(image_id, new_cat, bbox)
        if key in seen_keys:
            reasons["duplicate_annotation"] += 1
            continue
        seen_keys.add(key)

        if official_split == "val":
            dest_split = "val"
        elif _holdout_is_test(image_id, holdout_frac):
            dest_split = "test"
        else:
            dest_split = "train"

        out_im = {
            "id": image_id,
            "width": width,
            "height": height,
            "file_name": str(image.get("file_name") or f"{image_id}.jpg"),
            "license": 1,
            "original_split": official_split,
            "coco_url": image.get("original_url") or image.get("coco_url"),
        }
        buckets[dest_split]["images"][image_id] = out_im
        buckets[dest_split]["annotations"].append(
            {
                "id": int(ann.get("id") or 0),
                "image_id": image_id,
                "category_id": new_cat,
                "bbox": [round(v, 2) for v in bbox],
                "area": float(ann.get("area") or (bbox[2] * bbox[3])),
                "iscrowd": 0,
                "segmentation": seg,
                "original_category": original_name,
                "unified_category": unified,
                "source": "fashionpedia",
            }
        )
        reasons["kept"] += 1
        source_class_kept[original_name] += 1

    empty_images = 0
    for _image_id, image in images.items():
        # counted only if the image had annotations originally but none kept
        pass
    images_with_any_ann = {int(a["image_id"]) for a in coco.get("annotations") or []}
    kept_images = set()
    for bucket in buckets.values():
        kept_images.update(bucket["images"].keys())
    for image_id in images_with_any_ann:
        if image_id not in kept_images:
            empty_images += 1
    reasons["images_dropped_no_kept_instance"] += empty_images

    return {
        "split_name": split_name,
        "official_split": official_split,
        "buckets": buckets,
        "reasons": reasons,
        "source_class_kept": source_class_kept,
        "source_class_dropped": source_class_dropped,
        "tiny_flagged": tiny_flagged,
        "source_images": len(images),
        "source_annotations": anns_in,
    }


def merge_results(parts: Iterable[dict[str, Any]], label_map: UnifiedLabelMap) -> dict[str, Any]:
    images: dict[str, dict[int, dict[str, Any]]] = {"train": {}, "val": {}, "test": {}}
    anns: dict[str, list[dict[str, Any]]] = {"train": [], "val": [], "test": []}
    reasons: Counter[str] = Counter()
    kept: Counter[str] = Counter()
    dropped: Counter[str] = Counter()
    tiny: Counter[str] = Counter()
    source_images = 0
    source_annotations = 0
    for part in parts:
        source_images += part["source_images"]
        source_annotations += part["source_annotations"]
        reasons.update(part["reasons"])
        kept.update(part["source_class_kept"])
        dropped.update(part["source_class_dropped"])
        tiny.update(part["tiny_flagged"])
        for split, bucket in part["buckets"].items():
            images[split].update(bucket["images"])
            anns[split].extend(bucket["annotations"])

    coco_out = {}
    next_ann_id = 1
    for split in ("train", "val", "test"):
        split_anns = []
        for ann in anns[split]:
            ann = dict(ann)
            ann["id"] = next_ann_id
            next_ann_id += 1
            split_anns.append(ann)
        coco_out[split] = {
            "info": {
                "description": "Adore clothing detection (Fashionpedia mapped, Milestone 3)",
                "version": "1.0",
                "year": 2026,
                "contributor": "Adore FYP dataset prep",
                "date_created": _utc_now(),
                "source": FASHIONPEDIA,
            },
            "licenses": [
                {
                    "id": 1,
                    "name": "Creative Commons Attribution 4.0 International",
                    "url": "https://creativecommons.org/licenses/by/4.0/",
                }
            ],
            "categories": label_map.coco_categories(),
            "images": sorted(images[split].values(), key=lambda im: int(im["id"])),
            "annotations": split_anns,
        }
    return {
        "coco": coco_out,
        "reasons": reasons,
        "source_class_kept": kept,
        "source_class_dropped": dropped,
        "tiny_flagged": tiny,
        "source_images": source_images,
        "source_annotations": source_annotations,
    }


def write_coco(coco_out: dict[str, Any], output_dir: Path) -> dict[str, Path]:
    ann_dir = output_dir / "annotations"
    ann_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "images" / "train").mkdir(parents=True, exist_ok=True)
    (output_dir / "images" / "val").mkdir(parents=True, exist_ok=True)
    (output_dir / "images" / "test").mkdir(parents=True, exist_ok=True)
    paths = {}
    for split, payload in coco_out.items():
        path = ann_dir / f"instances_{split}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths[split] = path
        print(f"wrote {path} images={len(payload['images'])} anns={len(payload['annotations'])}")
    return paths


def _zip_index(zip_path: Path) -> dict[str, str]:
    index: dict[str, str] = {}
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if name.endswith("/"):
                continue
            index[Path(name).name.lower()] = name
    return index


def copy_images_from_zips(
    coco_out: dict[str, Any],
    source_dir: Path,
    output_dir: Path,
) -> dict[str, Any]:
    zips = []
    for name in ("train2020.zip", "val_test2020.zip"):
        path = source_dir / name
        if path.is_file():
            zips.append(path)
    zip_indexes = [(path, _zip_index(path)) for path in zips]
    copied = 0
    missing = []
    zip_handles = [(path, zipfile.ZipFile(path), index) for path, index in zip_indexes]
    try:
        for split, payload in coco_out.items():
            dest_dir = output_dir / "images" / split
            dest_dir.mkdir(parents=True, exist_ok=True)
            for image in payload["images"]:
                src_name = Path(image["file_name"]).name
                dest = dest_dir / src_name
                image["file_name"] = dest.name
                if dest.is_file() and dest.stat().st_size > 0:
                    copied += 1
                    continue
                found = None
                for _zip_path, zf, index in zip_handles:
                    member = index.get(src_name.lower())
                    if member:
                        dest.write_bytes(zf.read(member))
                        found = dest
                        break
                if found is None:
                    matches = [p for p in source_dir.rglob(src_name) if p.is_file()]
                    if matches:
                        dest.write_bytes(matches[0].read_bytes())
                        found = dest
                if found is None:
                    missing.append({"split": split, "file_name": src_name, "image_id": image["id"]})
                else:
                    copied += 1
            print(f"images {split}: copied so far {copied}, missing {len(missing)}")
    finally:
        for _path, zf, _index in zip_handles:
            zf.close()
    return {"copied": copied, "missing": missing}


def copy_images_from_huggingface(
    coco_out: dict[str, Any],
    output_dir: Path,
    cache_dir: Path,
    splits: tuple[str, ...] = ("train", "val", "test"),
    max_images: int | None = None,
) -> dict[str, Any]:
    """Copy images from detection-datasets/fashionpedia by image_id.

    Used when official zips are not local. Boxes/masks still come from official
    COCO JSON. An image is skipped if width/height do not match the JSON.
    """
    needed: dict[int, tuple[str, dict[str, Any], Path]] = {}
    for split in splits:
        payload = coco_out.get(split)
        if not payload:
            continue
        dest_dir = output_dir / "images" / split
        dest_dir.mkdir(parents=True, exist_ok=True)
        for image in payload["images"]:
            dest = dest_dir / Path(image["file_name"]).name
            image["file_name"] = dest.name
            if dest.is_file() and dest.stat().st_size > 0:
                continue
            needed[int(image["id"])] = (split, image, dest)
            if max_images is not None and len(needed) >= max_images:
                break
        if max_images is not None and len(needed) >= max_images:
            break
    if not needed:
        return {"copied": 0, "missing": [], "skipped_size_mismatch": 0, "source": "huggingface"}

    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(cache_dir))
    print(f"fetching {len(needed)} images from HuggingFace detection-datasets/fashionpedia", flush=True)
    from datasets import load_dataset

    copied = 0
    mismatch = 0
    for split_name in ("val", "train"):
        if not needed:
            break
        ds = load_dataset("detection-datasets/fashionpedia", split=split_name)
        for row in ds:
            image_id = int(row["image_id"])
            if image_id not in needed:
                continue
            split, image, dest = needed.pop(image_id)
            pil = row["image"]
            if int(pil.size[0]) != int(image["width"]) or int(pil.size[1]) != int(image["height"]):
                mismatch += 1
                needed[image_id] = (split, image, dest)
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            pil.convert("RGB").save(dest, format="JPEG", quality=95)
            copied += 1
            if copied % 50 == 0:
                print(f"  hf copied {copied}, remaining {len(needed)}", flush=True)
            if not needed:
                break
    missing = [{"split": s, "file_name": p.name, "image_id": i} for i, (s, _im, p) in needed.items()]
    print(f"hf images copied={copied} mismatch={mismatch} missing={len(missing)}", flush=True)
    return {
        "copied": copied,
        "missing": missing,
        "skipped_size_mismatch": mismatch,
        "source": "huggingface",
    }


def hash_images(coco_out: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    exact: dict[str, list[tuple[str, int]]] = defaultdict(list)
    perceptual: list[tuple[int, str, int, int]] = []
    hashed = 0
    for split, payload in coco_out.items():
        for image in payload["images"]:
            path = output_dir / "images" / split / Path(image["file_name"]).name
            if not path.is_file():
                continue
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            exact[digest].append((split, int(image["id"])))
            try:
                with Image.open(path) as im:
                    small = im.convert("RGB").resize((8, 8), Image.Resampling.BILINEAR)
                    ahash = average_hash_bytes(small.tobytes(), 8, 8)
                perceptual.append((ahash, split, int(image["id"]), hashed))
            except OSError:
                pass
            hashed += 1
    exact_dups = {k: v for k, v in exact.items() if len(v) > 1}
    cross_split = []
    for _digest, locs in exact_dups.items():
        splits = {s for s, _i in locs}
        if len(splits) > 1:
            cross_split.append(locs)
    near = []
    # Compare only hashes that collide in the top 16 bits to keep this tractable.
    buckets: dict[int, list[tuple[int, str, int]]] = defaultdict(list)
    for ahash, split, image_id, _i in perceptual:
        buckets[ahash >> 48].append((ahash, split, image_id))
    for group in buckets.values():
        if len(group) < 2:
            continue
        for i, (ha, sa, ia) in enumerate(group):
            for hb, sb, ib in group[i + 1 :]:
                if ha == hb:
                    continue
                if hamming64(ha, hb) <= 4 and {sa, sb} != {sa}:
                    near.append(((sa, ia), (sb, ib), hamming64(ha, hb)))
                elif hamming64(ha, hb) <= 4 and sa != sb:
                    near.append(((sa, ia), (sb, ib), hamming64(ha, hb)))
    return {
        "images_hashed": hashed,
        "exact_duplicate_groups": len(exact_dups),
        "exact_duplicate_examples": list(exact_dups.values())[:20],
        "cross_split_exact": cross_split[:50],
        "cross_split_exact_count": len(cross_split),
        "near_duplicate_cross_split_count": len(near),
        "near_duplicate_examples": near[:20],
    }


def class_stats(coco_out: dict[str, Any], label_map: UnifiedLabelMap) -> dict[str, Any]:
    rows = []
    total_instances = sum(len(coco_out[s]["annotations"]) for s in coco_out)
    total_images = sum(len(coco_out[s]["images"]) for s in coco_out)
    for name in label_map.detector_classes:
        cat_id = label_map.class_id(name)
        by_split = {}
        image_ids = set()
        n_inst = 0
        for split, payload in coco_out.items():
            ids = [a for a in payload["annotations"] if a["category_id"] == cat_id]
            imgs = {a["image_id"] for a in ids}
            by_split[split] = {"instances": len(ids), "images": len(imgs)}
            image_ids.update(imgs)
            n_inst += len(ids)
        rows.append(
            {
                "class": name,
                "category": label_map.category_of.get(name),
                "instances": n_inst,
                "images": len(image_ids),
                "pct_instances": round(100.0 * n_inst / total_instances, 3) if total_instances else 0.0,
                "splits": by_split,
            }
        )
    return {
        "total_images": total_images,
        "total_instances": total_instances,
        "per_class": rows,
        "split_counts": {
            split: {"images": len(payload["images"]), "instances": len(payload["annotations"])}
            for split, payload in coco_out.items()
        },
    }


def difficult_class_stats(stats: dict[str, Any]) -> dict[str, Any]:
    names = ["dress", "skirt", "bag", "trousers", "shirt", "jacket", "sweater", "shoes"]
    by_name = {row["class"]: row for row in stats["per_class"]}
    return {name: by_name.get(name) for name in names}


def drop_missing_image_records(
    coco_out: dict[str, Any], missing: list[dict[str, Any]]
) -> dict[str, Any]:
    missing_ids = {(m["split"], int(m["image_id"])) for m in missing}
    removed_images = 0
    removed_anns = 0
    for split, payload in coco_out.items():
        keep_ids = {int(im["id"]) for im in payload["images"] if (split, int(im["id"])) not in missing_ids}
        before_im = len(payload["images"])
        before_ann = len(payload["annotations"])
        payload["images"] = [im for im in payload["images"] if int(im["id"]) in keep_ids]
        payload["annotations"] = [a for a in payload["annotations"] if int(a["image_id"]) in keep_ids]
        removed_images += before_im - len(payload["images"])
        removed_anns += before_ann - len(payload["annotations"])
    return {"removed_images": removed_images, "removed_annotations": removed_anns}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {path}")


def render_report(payload: dict[str, Any], dest: Path) -> None:
    stats = payload["class_stats"]
    reasons = payload["qc_reasons"]
    lines = [
        "# Dataset Preparation Report",
        "",
        "**Milestone 3 of 8 — dataset conversion and validation only.**",
        f"**Date:** {payload['created_at']}",
        "**Rule:** No Mask R-CNN training. No production inference edits.",
        "",
        "---",
        "",
        "## 1. Dataset sources",
        "",
        "### Used",
        "",
        f"- **Fashionpedia** ({FASHIONPEDIA['version']})",
        f"  - License: {FASHIONPEDIA['license']}",
        f"  - Paper: {FASHIONPEDIA['paper']}",
        f"  - Official images: {FASHIONPEDIA['images_expected']} (train {FASHIONPEDIA['train_images_expected']}, val {FASHIONPEDIA['val_images_expected']}, public test labels: none)",
        "  - Annotation format: COCO instances + polygons/RLE + attributes",
        "  - Destination of raw files: `ml_service/datasets/sources/fashionpedia/`",
        "  - Converted dataset: `ml_service/datasets/clothing_detection/`",
        "",
        "### Documented but not used",
        "",
    ]
    for name, why in EXCLUDED_SOURCES.items():
        lines.append(f"- **{name}**: {why}")
    lines += [
        "",
        "## 2–3. Versions and licenses",
        "",
        "| Dataset | Version | License | Used? |",
        "|---|---|---|---|",
        "| Fashionpedia | 2020 CVDF/iFashionist | CC BY 4.0 | YES |",
        "| DeepFashion2 | CVPR 2019 | Academic non-commercial; password form; no commercial license | NO |",
        "| Local Adore / gates / outfit20 / Grigorev / HF crops | on-disk classification | mixed / private | NO as detector GT |",
        "",
        "Fashionpedia attribution: Jia et al., *Fashionpedia: Ontology, Segmentation, and an Attribute Localization Dataset*, ECCV 2020.",
        "",
        "## 4–7. Images and annotations processed",
        "",
        f"- Source images in JSON: **{payload['source_images']}**",
        f"- Source annotations in JSON: **{payload['source_annotations']}**",
        f"- Kept images: **{stats['total_images']}**",
        f"- Kept instances: **{stats['total_instances']}**",
        f"- Images copied from zip/source: **{payload.get('copy', {}).get('copied', 0)}**",
        f"- Missing image files after copy: **{len(payload.get('copy', {}).get('missing', []))}**",
        "",
        "### QC exclusion counts (annotations unless noted)",
        "",
        "| Reason | Count |",
        "|---|---:|",
    ]
    for key, value in sorted(reasons.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"| {key} | {value} |")
    dropped = payload.get("source_class_dropped") or {}
    kept_src = payload.get("source_class_kept") or {}
    ambiguous = {
        "top, t-shirt, sweatshirt",
        "cardigan",
        "vest",
        "cape",
        "headband, head covering, hair accessory",
    }
    amb_rows = [(k, v) for k, v in dropped.items() if k in ambiguous]
    part_rows = [(k, v) for k, v in dropped.items() if k not in ambiguous]
    lines += [
        "",
        "### Source classes kept (after mapping)",
        "",
        "| Fashionpedia class | Instances kept |",
        "|---|---:|",
    ]
    for name, count in sorted(kept_src.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {name} | {count} |")
    lines += [
        "",
        "### Ambiguous / DATA REQUIRED labels excluded (not remapped)",
        "",
        "| Fashionpedia class | Instances excluded | Why |",
        "|---|---:|---|",
        "| top, t-shirt, sweatshirt | "
        f"{dropped.get('top, t-shirt, sweatshirt', 0)} | mixed t-shirt/sweatshirt; not mapped to shirt |",
        f"| cardigan | {dropped.get('cardigan', 0)} | not sweater or hoodie |",
        f"| vest | {dropped.get('vest', 0)} | not jacket or shirt |",
        f"| cape | {dropped.get('cape', 0)} | not jacket |",
        "| headband, head covering, hair accessory | "
        f"{dropped.get('headband, head covering, hair accessory', 0)} | not hat, hijab, or dupatta |",
        "",
        f"Ambiguous labels excluded: **{sum(v for _, v in amb_rows)}**",
        f"Garment-part / other non-detector classes excluded: **{sum(v for _, v in part_rows)}**",
        "",
        "### Other excluded Fashionpedia classes (parts and out-of-vocab garments)",
        "",
        "| Fashionpedia class | Instances excluded |",
        "|---|---:|",
    ]
    for name, count in sorted(part_rows, key=lambda kv: -kv[1]):
        lines.append(f"| {name} | {count} |")
    lines += [
        "",
        "## 8. Final detector classes",
        "",
    ]
    for i, name in enumerate(payload["detector_classes"], start=1):
        lines.append(f"{i}. {name}")
    lines += [
        "",
        "DATA REQUIRED (excluded from this detector dataset): "
        + ", ".join(payload["data_required"]),
        "",
        "## 9. Instances per class",
        "",
        "| Class | Images | Instances | % of instances | train inst | val inst | test inst |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in stats["per_class"]:
        lines.append(
            f"| {row['class']} | {row['images']} | {row['instances']} | {row['pct_instances']} | "
            f"{row['splits']['train']['instances']} | {row['splits']['val']['instances']} | "
            f"{row['splits']['test']['instances']} |"
        )
    lines += [
        "",
        "## 10. Train / validation / test counts",
        "",
        "| Split | Images | Instances | Origin |",
        "|---|---:|---:|---|",
        f"| train | {stats['split_counts']['train']['images']} | {stats['split_counts']['train']['instances']} | official Fashionpedia train minus test holdout |",
        f"| val | {stats['split_counts']['val']['images']} | {stats['split_counts']['val']['instances']} | official Fashionpedia val (not reshuffled) |",
        f"| test | {stats['split_counts']['test']['images']} | {stats['split_counts']['test']['instances']} | deterministic 12% holdout of official train image ids |",
        "",
        "Reason for a train holdout: Fashionpedia does not publish test-set instance labels. "
        "Official val is kept intact. Holdout uses MD5(`adore-milestone3-fashionpedia-test-holdout:{image_id}`).",
        "",
        "## 11. Duplicate detection",
        "",
    ]
    dup = payload.get("duplicates") or {}
    if dup.get("skipped"):
        lines += [
            "Pixel hashing was **skipped** because image files were not fully copied "
            f"(`{dup.get('reason', 'image hashing skipped')}`).",
            "",
            "Split leakage is still prevented: official val image ids are never mixed into "
            "train/test, and the test holdout is a disjoint 12% of official train image ids.",
            "Duplicates removed: **0** (no pixel hashes computed yet).",
            "",
        ]
    else:
        lines += [
            f"- Exact filename collisions: {dup.get('filename_collisions', 0)}",
            f"- Perceptual near-duplicates across splits: {dup.get('cross_split_near_dups', 0)}",
            f"- Duplicates removed: {dup.get('removed', 0)}",
            "",
        ]
    lines += [
        "## 12. Invalid annotation results",
        "",
        "See the QC table above. Problematic rows were **reported and excluded**, not silently rewritten into fake boxes.",
        "",
        f"- Invalid or zero-area boxes dropped: {reasons.get('invalid_or_zero_bbox', 0)}",
        f"- Degenerate tiny objects dropped: {reasons.get('degenerate_tiny_dropped', 0)}",
        f"- Tiny objects kept but flagged: {reasons.get('tiny_kept_flagged', 0)}",
        f"- Images dropped because every instance was excluded: {reasons.get('images_dropped_no_kept_instance', 0)}",
        "",
        "",
        "## 13. Difficult-class statistics",
        "",
        "| Class | Images | Instances | % |",
        "|---|---:|---:|---:|",
    ]
    for name, row in (payload.get("difficult") or {}).items():
        if not row:
            lines.append(f"| {name} | 0 | 0 | 0 |")
        else:
            lines.append(f"| {name} | {row['images']} | {row['instances']} | {row['pct_instances']} |")
    under = [row["class"] for row in stats["per_class"] if row["instances"] < 200]
    dominant = sorted(stats["per_class"], key=lambda r: -r["instances"])[:3]
    lines += [
        "",
        "Underrepresented (<200 instances): " + (", ".join(under) if under else "none at that threshold"),
        "Dominant classes: " + ", ".join(f"{r['class']} ({r['instances']})" for r in dominant),
        "",
        "## 14. Missing-data classes",
        "",
        "Not in this instance dataset (DATA REQUIRED):",
        "",
    ]
    for name in payload["data_required"]:
        lines.append(f"- {name}")
    lines += [
        "",
        "## 15. Visualization results",
        "",
        f"Preview directory: `{payload.get('preview_dir', DEFAULT_PREVIEW)}`",
        f"Preview files written: {payload.get('preview_count', 0)}",
        "",
        "Scenes: normal outfit, multiple items, dress, skirt, bag, trousers, upperwear, footwear, accessories.",
        "Current previews are **geometry-only** when pixels are not copied (`--annotations-only`).",
        "They still show genuine instance masks/boxes: dress ≠ skirt, bag ≠ clothing, shoes as two instances.",
        "",
        "Open those images before Milestone 4. If a box covers the whole person as one garment, do not train.",
        "",
        "## 16. Known limitations",
        "",
        "- HuggingFace `detection-datasets/fashionpedia` was **not** used as GT: it has Pascal VOC boxes and **no masks**.",
        "- Official Fashionpedia val is small (~1.1k images). That split was kept official rather than inflating it.",
        "- `top, t-shirt, sweatshirt` is excluded, so t-shirt is DATA REQUIRED.",
        "- Footwear is a single `shoes` class; sneakers/loafers/flats stay on specialists.",
        "- `glasses` maps to `sunglasses` (closest optical accessory); some eyeglasses will be labelled sunglasses.",
        "- `coat` maps to `jacket`. Cape/vest/cardigan excluded.",
        "- Attributes (colour/pattern) are not classes; Fashionpedia `attribute_ids` are not expanded here.",
        "- Real-world Flutter photos are **not** in this training set. See `ml_service/datasets/clothing_detection/real_world_test/PLAN.md`.",
        "- DeepFashion2 was not mixed in (license + ambiguous tops + no accessories).",
        "",
        "## Reproducibility",
        "",
        "```text",
        "cd ml_service",
        r".\.venv\Scripts\python.exe -m training.prepare_detection_dataset --download",
        r".\.venv\Scripts\python.exe -m training.visualize_detection_dataset",
        "```",
        "",
        "No model was trained. Production inference was not modified.",
        "",
    ]
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {dest}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Prepare Adore clothing detection COCO dataset")
    p.add_argument("--label-map", type=Path, default=DEFAULT_MAP)
    p.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    p.add_argument("--download", action="store_true", help="Fetch Fashionpedia JSON (and official zips unless --annotations-only)")
    p.add_argument("--annotations-only", action="store_true", help="Do not download/copy images")
    p.add_argument("--images-from-hf", action="store_true", help="Copy images from HuggingFace by image_id (masks still from official JSON)")
    p.add_argument("--hf-cache", type=Path, default=DEFAULT_HF_CACHE)
    p.add_argument("--max-hf-images", type=int, default=None, help="Optional cap when fetching HuggingFace images")
    p.add_argument("--drop-missing-images", action="store_true", help="Remove COCO rows whose image files were not copied")
    p.add_argument("--fixture-dir", type=Path, default=None, help="Use a local mini COCO instead of Fashionpedia")
    p.add_argument("--min-area", type=float, default=16.0)
    p.add_argument("--min-side", type=float, default=2.0)
    p.add_argument("--flag-tiny-area", type=float, default=1024.0)
    p.add_argument("--holdout-frac", type=float, default=0.12)
    return p.parse_args(argv)


def run(args: argparse.Namespace) -> dict[str, Any]:
    label_map = load_label_map(args.label_map)
    if args.fixture_dir:
        train_json = args.fixture_dir / "instances_attributes_train2020.json"
        val_json = args.fixture_dir / "instances_attributes_val2020.json"
        source_dir = args.fixture_dir
    else:
        source_dir = args.source_dir
        if args.download:
            download_fashionpedia(source_dir, images=not args.annotations_only)
        train_json = source_dir / "instances_attributes_train2020.json"
        val_json = source_dir / "instances_attributes_val2020.json"
        if not train_json.is_file() or not val_json.is_file():
            raise FileNotFoundError(
                "Fashionpedia annotations are not on disk. Re-run with --download "
                "(this fetches CC BY 4.0 JSON from s3.amazonaws.com/ifashionist-dataset)."
            )

    train_coco = _load_coco(train_json)
    val_coco = _load_coco(val_json)
    train_part = convert_split(
        train_coco,
        label_map,
        "official_train",
        min_area=args.min_area,
        min_side=args.min_side,
        flag_tiny_area=args.flag_tiny_area,
        holdout_frac=args.holdout_frac,
        official_split="train",
    )
    val_part = convert_split(
        val_coco,
        label_map,
        "official_val",
        min_area=args.min_area,
        min_side=args.min_side,
        flag_tiny_area=args.flag_tiny_area,
        holdout_frac=0.0,
        official_split="val",
    )
    merged = merge_results([train_part, val_part], label_map)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    copy_info: dict[str, Any] = {"copied": 0, "missing": []}
    if getattr(args, "images_from_hf", False):
        copy_info = copy_images_from_huggingface(
            merged["coco"],
            output_dir,
            Path(getattr(args, "hf_cache", DEFAULT_HF_CACHE)),
            max_images=getattr(args, "max_hf_images", None),
        )
    elif not args.annotations_only:
        copy_info = copy_images_from_zips(merged["coco"], source_dir, output_dir)
    if getattr(args, "drop_missing_images", False) and copy_info.get("missing"):
        dropped = drop_missing_image_records(merged["coco"], copy_info["missing"])
        merged["reasons"]["missing_image_file_dropped"] = dropped["removed_images"]
        merged["reasons"]["missing_image_file_annotations_dropped"] = dropped["removed_annotations"]
    write_coco(merged["coco"], output_dir)
    stats = class_stats(merged["coco"], label_map)
    duplicates = {"skipped": True, "reason": "image hashing skipped"}
    copied_n = int(copy_info.get("copied") or 0)
    if copied_n:
        duplicates = hash_images(merged["coco"], output_dir)
    payload = {
        "created_at": _utc_now(),
        "detector_classes": label_map.detector_classes,
        "data_required": label_map.data_required,
        "source_images": merged["source_images"],
        "source_annotations": merged["source_annotations"],
        "qc_reasons": dict(merged["reasons"]),
        "source_class_kept": dict(merged["source_class_kept"]),
        "source_class_dropped": dict(merged["source_class_dropped"]),
        "tiny_flagged": dict(merged["tiny_flagged"]),
        "class_stats": stats,
        "difficult": difficult_class_stats(stats),
        "duplicates": duplicates,
        "copy": {
            "copied": copy_info.get("copied", 0),
            "missing": copy_info.get("missing", [])[:50],
            "missing_count": len(copy_info.get("missing", [])),
            "source": copy_info.get("source", "zip-or-loose"),
            "skipped_size_mismatch": copy_info.get("skipped_size_mismatch", 0),
        },
        "excluded_sources": EXCLUDED_SOURCES,
        "fashionpedia": FASHIONPEDIA,
        "holdout": {"frac": args.holdout_frac, "salt": HOLDOUT_SALT},
        "preview_dir": str(DEFAULT_PREVIEW),
        "preview_count": 0,
    }
    write_json(output_dir / "stats.json", payload)
    write_json(output_dir / "reports" / "qc_exclusions.json", payload["qc_reasons"])
    write_json(output_dir / "reports" / "class_balance.json", stats)
    write_json(output_dir / "reports" / "difficult_classes.json", payload["difficult"])
    render_report(payload, args.report)
    return payload


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    run(args)
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(SERVICE_ROOT))
    raise SystemExit(main())
