"""Milestone 3 conversion tests. No downloads, no training."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

from training.label_map import load_label_map
from training.prepare_detection_dataset import convert_split, merge_results, run
from training.visualize_detection_dataset import run as visualize

LABEL_MAP = Path(__file__).resolve().parents[1] / "taxonomy" / "unified_label_map.json"


def _write_image(path: Path, width: int, height: int, box, color) -> None:
    im = Image.new("RGB", (width, height), (240, 240, 240))
    draw = ImageDraw.Draw(im)
    x, y, w, h = box
    draw.rectangle([x, y, x + w, y + h], fill=color)
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, format="JPEG")


def _poly(box):
    x, y, w, h = box
    return [x, y, x + w, y, x + w, y + h, x, y + h]


def _mini_fashionpedia(root: Path) -> Path:
    """Official-shaped JSON with keep, reject, invalid, and tiny rows."""
    categories = [
        {"id": 1, "name": "shirt, blouse"},
        {"id": 2, "name": "top, t-shirt, sweatshirt"},
        {"id": 3, "name": "sweater"},
        {"id": 4, "name": "dress"},
        {"id": 5, "name": "skirt"},
        {"id": 6, "name": "pants"},
        {"id": 7, "name": "bag, wallet"},
        {"id": 8, "name": "shoe"},
        {"id": 9, "name": "jumpsuit"},
        {"id": 10, "name": "scarf"},
        {"id": 11, "name": "sleeve"},
        {"id": 12, "name": "jacket"},
        {"id": 13, "name": "hat"},
    ]
    shirt = [20, 20, 80, 90]
    trousers = [30, 110, 60, 80]
    bag = [110, 80, 40, 50]
    dress = [15, 20, 90, 170]
    skirt = [20, 100, 70, 70]
    shoes = [25, 190, 35, 20]
    images = [
        {"id": 101, "width": 160, "height": 220, "file_name": "outfit.jpg"},
        {"id": 102, "width": 160, "height": 220, "file_name": "dress.jpg"},
        {"id": 103, "width": 160, "height": 220, "file_name": "skirt.jpg"},
    ]
    anns = [
        {"id": 1, "image_id": 101, "category_id": 1, "bbox": shirt, "area": 80 * 90, "iscrowd": 0, "segmentation": [_poly(shirt)]},
        {"id": 2, "image_id": 101, "category_id": 6, "bbox": trousers, "area": 60 * 80, "iscrowd": 0, "segmentation": [_poly(trousers)]},
        {"id": 3, "image_id": 101, "category_id": 7, "bbox": bag, "area": 40 * 50, "iscrowd": 0, "segmentation": [_poly(bag)]},
        {"id": 4, "image_id": 101, "category_id": 8, "bbox": shoes, "area": 35 * 20, "iscrowd": 0, "segmentation": [_poly(shoes)]},
        {"id": 5, "image_id": 101, "category_id": 2, "bbox": [10, 10, 50, 40], "area": 2000, "iscrowd": 0, "segmentation": [_poly([10, 10, 50, 40])]},
        {"id": 6, "image_id": 101, "category_id": 11, "bbox": [20, 20, 20, 40], "area": 800, "iscrowd": 0, "segmentation": [_poly([20, 20, 20, 40])]},
        {"id": 7, "image_id": 101, "category_id": 1, "bbox": [-20, 10, 5, 5], "area": 25, "iscrowd": 0, "segmentation": [_poly([0, 10, 5, 5])]},
        {"id": 8, "image_id": 102, "category_id": 4, "bbox": dress, "area": 90 * 170, "iscrowd": 0, "segmentation": [_poly(dress)]},
        {"id": 9, "image_id": 102, "category_id": 3, "bbox": [20, 20, 40, 40], "area": 1600, "iscrowd": 0, "segmentation": [_poly([20, 20, 40, 40])]},
        {"id": 10, "image_id": 103, "category_id": 5, "bbox": skirt, "area": 70 * 70, "iscrowd": 0, "segmentation": [_poly(skirt)]},
        {"id": 11, "image_id": 103, "category_id": 9, "bbox": [15, 15, 80, 180], "area": 14400, "iscrowd": 0, "segmentation": [_poly([15, 15, 80, 180])]},
        {"id": 12, "image_id": 103, "category_id": 10, "bbox": [20, 10, 50, 20], "area": 1000, "iscrowd": 0, "segmentation": [_poly([20, 10, 50, 20])]},
        {"id": 13, "image_id": 103, "category_id": 12, "bbox": [10, 10, 40, 40], "area": 1600, "iscrowd": 0, "segmentation": []},
    ]
    train = {
        "info": {"description": "mini fixture"},
        "categories": categories,
        "images": images,
        "annotations": anns,
        "licenses": [],
    }
    val = {
        "info": {"description": "mini fixture val"},
        "categories": categories,
        "images": [
            {"id": 201, "width": 160, "height": 220, "file_name": "hat.jpg"},
        ],
        "annotations": [
            {
                "id": 50,
                "image_id": 201,
                "category_id": 13,
                "bbox": [40, 10, 60, 40],
                "area": 2400,
                "iscrowd": 0,
                "segmentation": [_poly([40, 10, 60, 40])],
            }
        ],
        "licenses": [],
    }
    root.mkdir(parents=True, exist_ok=True)
    (root / "instances_attributes_train2020.json").write_text(json.dumps(train), encoding="utf-8")
    (root / "instances_attributes_val2020.json").write_text(json.dumps(val), encoding="utf-8")
    _write_image(root / "outfit.jpg", 160, 220, shirt, (180, 40, 40))
    _write_image(root / "dress.jpg", 160, 220, dress, (160, 20, 90))
    _write_image(root / "skirt.jpg", 160, 220, skirt, (90, 40, 160))
    _write_image(root / "hat.jpg", 160, 220, [40, 10, 60, 40], (20, 90, 90))
    return root


def test_unsafe_maps_are_absent():
    mapping = load_label_map()
    assert mapping.fashionpedia["sweater"] == "sweater"
    assert mapping.fashionpedia["dress"] == "dress"
    assert mapping.fashionpedia["skirt"] == "skirt"
    assert mapping.fashionpedia["scarf"] == "scarf"
    assert mapping.fashionpedia["jumpsuit"] == "jumpsuit"
    assert "top, t-shirt, sweatshirt" not in mapping.fashionpedia
    unified, why = mapping.map_fashionpedia("top, t-shirt, sweatshirt")
    assert unified is None
    assert why == "rejected_taxonomy"


def test_fixture_conversion_keeps_instances_and_drops_ambiguous(tmp_path: Path):
    fixture = _mini_fashionpedia(tmp_path / "src")
    mapping = load_label_map()
    train = json.loads((fixture / "instances_attributes_train2020.json").read_text(encoding="utf-8"))
    part = convert_split(
        train,
        mapping,
        "official_train",
        min_area=16,
        min_side=2,
        flag_tiny_area=1024,
        holdout_frac=0.0,
        official_split="train",
    )
    kept_names = [a["unified_category"] for a in part["buckets"]["train"]["annotations"]]
    assert "shirt" in kept_names
    assert "trousers" in kept_names
    assert "bag" in kept_names
    assert "dress" in kept_names
    assert "skirt" in kept_names
    assert "jumpsuit" in kept_names
    assert "scarf" in kept_names
    assert "sweater" in kept_names
    assert "hoodie" not in kept_names
    assert "t-shirt" not in kept_names
    assert "dupatta" not in kept_names
    dropped = dict(part["source_class_dropped"])
    assert dropped.get("top, t-shirt, sweatshirt", 0) == 1
    assert dropped.get("sleeve", 0) == 1
    assert part["reasons"]["invalid_or_zero_bbox"] >= 1
    assert part["reasons"]["invalid_or_missing_segmentation"] >= 1


def test_end_to_end_fixture_writes_coco_and_previews(tmp_path: Path):
    fixture = _mini_fashionpedia(tmp_path / "src")
    output = tmp_path / "clothing_detection"
    report = tmp_path / "DATASET_PREPARATION_REPORT.md"
    payload = run(
        type(
            "Args",
            (),
            {
                "label_map": LABEL_MAP,
                "source_dir": fixture,
                "output_dir": output,
                "report": report,
                "download": False,
                "annotations_only": False,
                "fixture_dir": fixture,
                "min_area": 16.0,
                "min_side": 2.0,
                "flag_tiny_area": 1024.0,
                "holdout_frac": 0.0,
            },
        )()
    )
    train = json.loads((output / "annotations" / "instances_train.json").read_text(encoding="utf-8"))
    names = {c["name"] for c in train["categories"]}
    assert names == set(payload["detector_classes"])
    assert (output / "images" / "train" / "outfit.jpg").is_file()
    assert report.is_file()
    preview = tmp_path / "preview"
    written = visualize(output, preview, per_scene=1, seed=1, report_path=tmp_path / "preview_report.md")
    assert written >= 1
    assert (preview / "README.md").is_file()
    assert (tmp_path / "preview_report.md").is_file()


def test_merge_does_not_put_official_val_into_train(tmp_path: Path):
    fixture = _mini_fashionpedia(tmp_path / "src")
    mapping = load_label_map()
    train = json.loads((fixture / "instances_attributes_train2020.json").read_text(encoding="utf-8"))
    val = json.loads((fixture / "instances_attributes_val2020.json").read_text(encoding="utf-8"))
    merged = merge_results(
        [
            convert_split(train, mapping, "t", min_area=16, min_side=2, flag_tiny_area=1024, holdout_frac=0.0, official_split="train"),
            convert_split(val, mapping, "v", min_area=16, min_side=2, flag_tiny_area=1024, holdout_frac=0.0, official_split="val"),
        ],
        mapping,
    )
    val_ids = {im["id"] for im in merged["coco"]["val"]["images"]}
    train_ids = {im["id"] for im in merged["coco"]["train"]["images"]}
    assert 201 in val_ids
    assert 201 not in train_ids
    assert 101 in train_ids
