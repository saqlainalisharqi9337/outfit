"""Milestone 4.4 dataset-audit tests. No downloads, no training."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

from test_maskrcnn_pipeline import _mini_coco, _poly
from training.audit_dataset import audit_coco, classify_imbalance, compare_splits, write_outputs
from training.dataset import class_aware_select
from training.label_map import load_label_map


def _coco_with_problems(root: Path) -> dict:
    mapping = load_label_map()
    categories = mapping.coco_categories()
    shirt = [10, 10, 40, 50]
    images_dir = root / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", (80, 80), (200, 200, 200))
    ImageDraw.Draw(im).rectangle([10, 10, 50, 60], fill=(180, 40, 40))
    im.save(images_dir / "ok.jpg", format="JPEG")
    coco = {
        "images": [
            {"id": 1, "width": 80, "height": 80, "file_name": "ok.jpg"},
            {"id": 2, "width": 80, "height": 80, "file_name": "missing.jpg"},
            {"id": 3, "width": 80, "height": 80, "file_name": "empty.jpg"},
        ],
        "annotations": [
            {
                "id": 1,
                "image_id": 1,
                "category_id": mapping.class_id("shirt"),
                "bbox": shirt,
                "area": 2000,
                "iscrowd": 0,
                "segmentation": [_poly(shirt)],
            },
            {
                "id": 2,
                "image_id": 1,
                "category_id": mapping.class_id("shirt"),
                "bbox": shirt,
                "area": 2000,
                "iscrowd": 0,
                "segmentation": [_poly(shirt)],
            },
            {
                "id": 3,
                "image_id": 1,
                "category_id": 99,
                "bbox": [5, 5, 10, 10],
                "area": 100,
                "iscrowd": 0,
                "segmentation": [_poly([5, 5, 10, 10])],
            },
            {
                "id": 4,
                "image_id": 1,
                "category_id": mapping.class_id("dress"),
                "bbox": [70, 10, -4, 8],
                "area": 0,
                "iscrowd": 0,
                "segmentation": [_poly([70, 10, 4, 8])],
            },
            {
                "id": 5,
                "image_id": 1,
                "category_id": mapping.class_id("bag"),
                "bbox": [90, 90, 20, 20],
                "area": 400,
                "iscrowd": 0,
                "segmentation": [_poly([90, 90, 20, 20])],
            },
        ],
        "categories": categories,
    }
    return coco


def test_audit_counts_known_classes(tmp_path: Path):
    images_dir, ann_path = _mini_coco(tmp_path)
    coco = json.loads(ann_path.read_text(encoding="utf-8"))
    approved = load_label_map().detector_classes
    result = audit_coco(coco, image_dir=images_dir, split="train", approved=approved)
    rows = result["class_rows"]
    assert rows["shirt"]["num_annotations"] == 1
    assert rows["trousers"]["num_annotations"] == 1
    assert rows["shoes"]["num_annotations"] == 1
    assert rows["bag"]["num_annotations"] == 1
    assert rows["dress"]["num_annotations"] == 1
    assert rows["hat"]["num_annotations"] == 1
    assert rows["shirt"]["num_boxes"] == 1
    assert rows["shirt"]["num_masks"] == 1
    assert result["total_images"] == 2
    assert result["total_annotations"] == 6
    assert result["images_with_zero_annotations"] == 0


def test_audit_detects_invalid_boxes_and_unknown_class_ids(tmp_path: Path):
    coco = _coco_with_problems(tmp_path)
    approved = load_label_map().detector_classes
    result = audit_coco(coco, image_dir=tmp_path / "images", split="train", approved=approved)
    assert result["errors"].get("unknown_class_id", 0) == 1
    assert result["errors"].get("non_positive_wh", 0) >= 1
    assert result["errors"].get("bbox_outside_image", 0) >= 1
    assert result["errors"].get("duplicate_annotation", 0) >= 1
    assert result["errors"].get("missing_image_file", 0) >= 1
    assert result["images_with_zero_annotations"] == 2  # missing.jpg has no anns? wait id 2 and 3
    assert result["class_rows"]["shirt"]["num_annotations"] == 2


def test_split_overlap_detection():
    approved = load_label_map().detector_classes
    train = {
        "images": [{"id": 1, "width": 10, "height": 10, "file_name": "same.jpg"}],
        "annotations": [
            {"id": 1, "image_id": 1, "category_id": 1, "bbox": [1, 1, 4, 4], "segmentation": [[1, 1, 5, 1, 5, 5, 1, 5]]}
        ],
        "categories": load_label_map().coco_categories(),
    }
    val = {
        "images": [{"id": 1, "width": 10, "height": 10, "file_name": "same.jpg"}],
        "annotations": [
            {"id": 2, "image_id": 1, "category_id": 7, "bbox": [1, 1, 4, 4], "segmentation": [[1, 1, 5, 1, 5, 5, 1, 5]]}
        ],
        "categories": load_label_map().coco_categories(),
    }
    audits = {
        "train": audit_coco(train, image_dir=None, split="train", approved=approved),
        "val": audit_coco(val, image_dir=None, split="val", approved=approved),
    }
    compared = compare_splits(audits)
    assert compared["overlap_counts"]["train_val_filename"] == 1
    assert compared["overlap_counts"]["train_val_image_id"] == 1
    assert "shirt" in compared["class_gaps"]["in_train_not_val"]
    assert "dress" in compared["class_gaps"]["in_val_not_train"]


def test_imbalance_and_write_outputs(tmp_path: Path):
    rows = {
        "shoes": {"num_annotations": 1000, "class_name": "shoes"},
        "dress": {"num_annotations": 800, "class_name": "dress"},
        "shirt": {"num_annotations": 50, "class_name": "shirt"},
        "watch": {"num_annotations": 5, "class_name": "watch"},
    }
    # classify_imbalance expects full class_rows with num_annotations only used
    mapping = load_label_map()
    full = {name: {"num_annotations": rows.get(name, {}).get("num_annotations", 40), "class_name": name} for name in mapping.detector_classes}
    full["shoes"]["num_annotations"] = 1000
    full["dress"]["num_annotations"] = 800
    full["watch"]["num_annotations"] = 5
    result = classify_imbalance(full)
    assert "shoes" in result["high_frequency"]
    assert "watch" in result["suspiciously_few"]
    payload = {
        "generated_at": "now",
        "background_id": 0,
        "class_mapping": [{"class_id": 1, "class_name": "shirt"}],
        "totals": {"images": 1, "annotations": 1, "classes_found": 15},
        "per_class": [
            {
                "class_id": 1,
                "class_name": "shirt",
                "num_images": 1,
                "num_annotations": 1,
                "num_boxes": 1,
                "num_masks": 1,
                "pct_annotations": 100.0,
                "min_box_width": 1,
                "min_box_height": 1,
                "avg_box_width": 1,
                "avg_box_height": 1,
                "max_box_width": 1,
                "max_box_height": 1,
                "images_with_invalid": 0,
                "tiny_boxes": 0,
            }
        ],
        "imbalance": result,
        "integrity_errors": {},
        "split_checks": {"overlap_counts": {}, "class_gaps": {}},
        "recommended_experiment": {
            "max_train_images": 500,
            "max_val_images": 100,
            "epochs": 3,
            "subset_mode": "class_aware",
            "selection": "test",
        },
    }
    write_outputs(payload, tmp_path)
    assert (tmp_path / "dataset_audit.json").is_file()
    assert (tmp_path / "dataset_audit.csv").is_file()
    assert (tmp_path / "DATASET_AUDIT_REPORT.md").is_file()


def test_class_aware_subset_keeps_rare_class(tmp_path: Path):
    images_dir, ann_path = _mini_coco(tmp_path)
    coco = json.loads(ann_path.read_text(encoding="utf-8"))
    records = []
    anns_by = {}
    from collections import defaultdict

    grouped = defaultdict(list)
    for ann in coco["annotations"]:
        grouped[int(ann["image_id"])].append(ann)
    for image in coco["images"]:
        records.append({"image": image, "path": images_dir / image["file_name"], "anns": grouped[int(image["id"])]})
    mapping = load_label_map()
    cat_id_to_label = {int(c["id"]): mapping.class_id(c["name"]) for c in coco["categories"]}
    selected = class_aware_select(records, cat_id_to_label, max_images=1, seed=0)
    assert len(selected) == 1
    names = {mapping.detector_classes[cat_id_to_label[int(a["category_id"])] - 1] for a in selected[0]["anns"]}
    assert names
