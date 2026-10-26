"""Milestone 4.2 pipeline tests. No downloads, no full training, no production edits."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import torch
from PIL import Image, ImageDraw
from torch.utils.data import DataLoader

from training.dataset import (
    BACKGROUND_ID,
    NUM_CLASSES,
    NUM_FOREGROUND,
    ClothingDetectionDataset,
    collate_fn,
    decode_rle,
    segmentation_to_mask,
)
from training.evaluate_maskrcnn import planned_metric_names
from training.label_map import load_label_map
from training.train_maskrcnn import build_maskrcnn, head_class_counts

pytest.importorskip("torchvision")


def _poly(box):
    x, y, w, h = box
    return [x, y, x + w, y, x + w, y + h, x, y + h]


def _write_rgb(path: Path, width: int, height: int, fills: list[tuple[list[int], tuple[int, int, int]]]) -> None:
    im = Image.new("RGB", (width, height), (240, 240, 240))
    draw = ImageDraw.Draw(im)
    for box, color in fills:
        x, y, w, h = box
        draw.rectangle([x, y, x + w, y + h], fill=color)
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, format="JPEG")


def _uncompressed_rle(mask: np.ndarray) -> dict:
    flat = mask.reshape((-1,), order="F")
    counts: list[int] = []
    prev = 0
    run = 0
    for value in flat.tolist():
        bit = int(value)
        if bit == prev:
            run += 1
        else:
            counts.append(run)
            run = 1
            prev = bit
    counts.append(run)
    h, w = mask.shape
    return {"size": [h, w], "counts": counts}


def _mini_coco(root: Path) -> tuple[Path, Path]:
    mapping = load_label_map()
    categories = mapping.coco_categories()
    images_dir = root / "images"
    ann_path = root / "instances.json"
    shirt = [20, 20, 80, 90]
    trousers = [30, 110, 60, 80]
    shoes = [25, 190, 35, 20]
    bag = [110, 80, 40, 50]
    dress = [18, 16, 90, 170]
    hat = [40, 8, 50, 28]
    images = [
        {"id": 1, "width": 160, "height": 220, "file_name": "outfit.jpg"},
        {"id": 2, "width": 160, "height": 220, "file_name": "dress.jpg"},
    ]
    rle_mask = np.zeros((220, 160), dtype=np.uint8)
    rle_mask[190:210, 25:60] = 1
    anns = [
        {
            "id": 1,
            "image_id": 1,
            "category_id": mapping.class_id("shirt"),
            "bbox": shirt,
            "area": 80 * 90,
            "iscrowd": 0,
            "segmentation": [_poly(shirt)],
        },
        {
            "id": 2,
            "image_id": 1,
            "category_id": mapping.class_id("trousers"),
            "bbox": trousers,
            "area": 60 * 80,
            "iscrowd": 0,
            "segmentation": [_poly(trousers)],
        },
        {
            "id": 3,
            "image_id": 1,
            "category_id": mapping.class_id("shoes"),
            "bbox": shoes,
            "area": 35 * 20,
            "iscrowd": 0,
            "segmentation": _uncompressed_rle(rle_mask),
        },
        {
            "id": 4,
            "image_id": 1,
            "category_id": mapping.class_id("bag"),
            "bbox": bag,
            "area": 40 * 50,
            "iscrowd": 0,
            "segmentation": [_poly(bag)],
        },
        {
            "id": 5,
            "image_id": 2,
            "category_id": mapping.class_id("dress"),
            "bbox": dress,
            "area": 90 * 170,
            "iscrowd": 0,
            "segmentation": [_poly(dress)],
        },
        {
            "id": 6,
            "image_id": 2,
            "category_id": mapping.class_id("hat"),
            "bbox": hat,
            "area": 50 * 28,
            "iscrowd": 0,
            "segmentation": [_poly(hat)],
        },
    ]
    coco = {"images": images, "annotations": anns, "categories": categories}
    ann_path.write_text(json.dumps(coco), encoding="utf-8")
    _write_rgb(
        images_dir / "outfit.jpg",
        160,
        220,
        [(shirt, (180, 40, 40)), (trousers, (40, 80, 180)), (shoes, (20, 20, 20)), (bag, (40, 140, 70))],
    )
    _write_rgb(images_dir / "dress.jpg", 160, 220, [(dress, (160, 20, 90)), (hat, (20, 90, 90))])
    return images_dir, ann_path


def test_taxonomy_has_15_foreground_classes_and_background_zero():
    mapping = load_label_map()
    assert mapping.detector_classes == [
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
    assert len(mapping.detector_classes) == NUM_FOREGROUND == 15
    assert BACKGROUND_ID == 0
    assert NUM_CLASSES == 16
    assert mapping.class_id("shirt") == 1
    assert mapping.class_id("sunglasses") == 15
    for name in mapping.detector_classes:
        assert 1 <= mapping.class_id(name) <= 15


def test_rle_and_polygon_masks_match_image_shape():
    poly = segmentation_to_mask([[10, 10, 40, 10, 40, 40, 10, 40]], 50, 60)
    assert poly.shape == (50, 60)
    assert int(poly.max()) == 1
    mask = np.zeros((8, 10), dtype=np.uint8)
    mask[2:6, 3:7] = 1
    decoded = decode_rle(_uncompressed_rle(mask), 8, 10)
    assert decoded.shape == (8, 10)
    assert np.array_equal(decoded, mask)


def test_dataset_target_shapes_and_label_range(tmp_path: Path):
    images_dir, ann_path = _mini_coco(tmp_path)
    dataset = ClothingDetectionDataset(images_dir, ann_path)
    assert len(dataset) == 2
    image, target = dataset[0]
    assert isinstance(image, torch.Tensor)
    assert image.ndim == 3 and image.shape[0] == 3
    assert isinstance(target, dict)
    n = int(target["labels"].shape[0])
    assert n == 4
    assert tuple(target["boxes"].shape) == (n, 4)
    assert tuple(target["labels"].shape) == (n,)
    assert tuple(target["masks"].shape) == (n, image.shape[1], image.shape[2])
    assert int(target["labels"].min()) >= 1
    assert int(target["labels"].max()) <= 15
    names = [dataset.label_names[int(i) - 1] for i in target["labels"].tolist()]
    assert names == ["shirt", "trousers", "shoes", "bag"]
    for box in target["boxes"]:
        x1, y1, x2, y2 = (float(v) for v in box.tolist())
        assert x1 < x2 and y1 < y2
        assert x1 >= 0 and y1 >= 0
        assert x2 <= image.shape[2] and y2 <= image.shape[1]


def test_collate_handles_variable_instance_counts(tmp_path: Path):
    images_dir, ann_path = _mini_coco(tmp_path)
    dataset = ClothingDetectionDataset(images_dir, ann_path)
    loader = DataLoader(dataset, batch_size=2, shuffle=False, num_workers=0, collate_fn=collate_fn)
    images, targets = next(iter(loader))
    assert len(images) == 2
    assert len(targets) == 2
    assert int(targets[0]["labels"].shape[0]) == 4
    assert int(targets[1]["labels"].shape[0]) == 2
    assert targets[0]["masks"].shape[0] != targets[1]["masks"].shape[0]


def test_model_heads_output_16_classes_without_download():
    model = build_maskrcnn(NUM_CLASSES, pretrained=False, min_size=32, max_size=64)
    box_classes, mask_classes = head_class_counts(model)
    assert box_classes == 16
    assert mask_classes == 16
    assert int(model.roi_heads.box_predictor.cls_score.out_features) == 16
    assert int(model.roi_heads.mask_predictor.mask_fcn_logits.out_channels) == 16


def test_evaluation_skeleton_lists_future_metrics():
    names = planned_metric_names()
    assert "mAP@50" in names
    assert "mAP@50:95" in names
    assert "per-class AP" in names
