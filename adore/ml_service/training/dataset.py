"""PyTorch Dataset for the converted 15-class clothing detection COCO set.

Not used by FastAPI production inference. Does not invent masks from boxes.
"""

from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageOps
from torch.utils.data import Dataset

SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from training.label_map import UnifiedLabelMap, load_label_map

DEFAULT_DATASET_ROOT = SERVICE_ROOT / "datasets" / "clothing_detection"
NUM_FOREGROUND = 15
NUM_CLASSES = 16  # background + 15 clothing classes
BACKGROUND_ID = 0


class AnnotationError(ValueError):
    """Invalid instance that must not be silently turned into fake GT."""


def coco_xywh_to_xyxy(bbox: list[float]) -> list[float]:
    x, y, w, h = (float(v) for v in bbox)
    return [x, y, x + w, y + h]


def _decode_coco_rle_counts(s: str) -> list[int]:
    """COCO compressed RLE (maskApi.c rleFrString) without pycocotools."""
    p = 0
    counts: list[int] = []
    while p < len(s):
        x = 0
        k = 0
        more = True
        while more:
            c = ord(s[p]) - 48
            p += 1
            x |= (c & 0x1F) << (5 * k)
            more = bool(c & 0x20)
            k += 1
            if not more and (c & 0x10):
                x |= -1 << (5 * k)
        if len(counts) > 2:
            x += counts[-2]
        counts.append(int(x))
    return counts


def decode_rle(segmentation: dict[str, Any], height: int, width: int) -> np.ndarray:
    size = segmentation.get("size")
    counts = segmentation.get("counts")
    if not size or counts is None:
        raise AnnotationError("RLE segmentation missing size or counts")
    h, w = int(size[0]), int(size[1])
    if h != height or w != width:
        raise AnnotationError(f"RLE size {(h, w)} does not match image {(height, width)}")
    if isinstance(counts, str):
        counts_list = _decode_coco_rle_counts(counts)
    elif isinstance(counts, list):
        counts_list = [int(c) for c in counts]
    else:
        raise AnnotationError(f"unsupported RLE counts type {type(counts).__name__}")
    total = h * w
    flat = np.zeros(total, dtype=np.uint8)
    idx = 0
    val = 0
    for run in counts_list:
        if run < 0:
            raise AnnotationError("negative RLE run length")
        end = idx + run
        if end > total:
            raise AnnotationError(f"RLE overflows mask ({end} > {total})")
        if val:
            flat[idx:end] = 1
        idx = end
        val = 1 - val
    if idx != total:
        raise AnnotationError(f"RLE underfills mask ({idx} != {total})")
    return flat.reshape((h, w), order="F")


def decode_polygons(segmentation: list[Any], height: int, width: int) -> np.ndarray:
    polys = segmentation if segmentation and isinstance(segmentation[0], (list, tuple)) else [segmentation]
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    drawn = False
    for poly in polys:
        if not isinstance(poly, (list, tuple)) or len(poly) < 6 or len(poly) % 2:
            raise AnnotationError(f"polygon length {len(poly) if isinstance(poly, (list, tuple)) else None} is invalid")
        pts = [(float(poly[i]), float(poly[i + 1])) for i in range(0, len(poly), 2)]
        draw.polygon(pts, outline=1, fill=1)
        drawn = True
    if not drawn:
        raise AnnotationError("empty polygon list")
    return np.array(mask, dtype=np.uint8)


def segmentation_to_mask(segmentation: Any, height: int, width: int) -> np.ndarray:
    if segmentation is None:
        raise AnnotationError("missing segmentation; refusing to invent a box mask")
    if isinstance(segmentation, dict):
        return decode_rle(segmentation, height, width)
    if isinstance(segmentation, list):
        if not segmentation:
            raise AnnotationError("empty segmentation list; refusing to invent a box mask")
        return decode_polygons(segmentation, height, width)
    raise AnnotationError(f"unsupported segmentation type {type(segmentation).__name__}")


def validate_instance(
    *,
    image_id: int,
    ann_id: int,
    box_xyxy: list[float],
    label: int,
    mask: np.ndarray,
    width: int,
    height: int,
) -> tuple[list[float], int, np.ndarray]:
    x1, y1, x2, y2 = (float(v) for v in box_xyxy)
    if not (1 <= int(label) <= NUM_FOREGROUND):
        raise AnnotationError(f"image {image_id} ann {ann_id}: label {label} not in 1..{NUM_FOREGROUND}")
    if mask.shape != (height, width):
        raise AnnotationError(
            f"image {image_id} ann {ann_id}: mask shape {mask.shape} != image {(height, width)}"
        )
    x1 = min(max(x1, 0.0), float(width))
    y1 = min(max(y1, 0.0), float(height))
    x2 = min(max(x2, 0.0), float(width))
    y2 = min(max(y2, 0.0), float(height))
    if not (x1 < x2 and y1 < y2):
        raise AnnotationError(f"image {image_id} ann {ann_id}: box {[x1, y1, x2, y2]} has no positive area")
    if (x2 - x1) < 1.0 or (y2 - y1) < 1.0:
        raise AnnotationError(f"image {image_id} ann {ann_id}: box too small {[x1, y1, x2, y2]}")
    if int(mask.max()) < 1:
        raise AnnotationError(f"image {image_id} ann {ann_id}: empty mask")
    return [x1, y1, x2, y2], int(label), mask


def collate_fn(batch: list[tuple[torch.Tensor, dict[str, torch.Tensor]]]):
    """Standard detection collate: tuple of images and tuple of targets."""
    return tuple(zip(*batch))


def class_aware_select(
    records: list[dict[str, Any]],
    cat_id_to_label: dict[int, int],
    max_images: int,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Greedy round-robin so rare classes are not dropped from a small subset.

    1. Group images by each foreground class they contain.
    2. Shuffle each group with ``seed``.
    3. Repeatedly take the next unused image from the currently rarest class
       until ``max_images`` is reached.
    4. If still short, fill from leftover images.
    """
    if max_images is None or max_images >= len(records):
        return list(records)
    rng = random.Random(seed)
    by_class: dict[int, list[int]] = defaultdict(list)
    for index, row in enumerate(records):
        seen: set[int] = set()
        for ann in row["anns"]:
            cat_id = int(ann.get("category_id") or 0)
            if cat_id not in cat_id_to_label:
                continue
            label = cat_id_to_label[cat_id]
            if label not in seen:
                by_class[label].append(index)
                seen.add(label)
    for label in by_class:
        rng.shuffle(by_class[label])
    selected: list[int] = []
    used: set[int] = set()
    pointers = {label: 0 for label in by_class}
    order = sorted(by_class, key=lambda lab: (len(by_class[lab]), lab))
    while len(selected) < max_images and by_class:
        added = False
        for label in order:
            while pointers[label] < len(by_class[label]):
                idx = by_class[label][pointers[label]]
                pointers[label] += 1
                if idx in used:
                    continue
                used.add(idx)
                selected.append(idx)
                added = True
                break
            if len(selected) >= max_images:
                break
        if not added:
            break
    if len(selected) < max_images:
        rest = [i for i in range(len(records)) if i not in used]
        rng.shuffle(rest)
        selected.extend(rest[: max_images - len(selected)])
    return [records[i] for i in selected[:max_images]]


WEAK_CLASS_NAMES = ("shirt", "scarf", "belt", "watch", "skirt")


def weak_class_select(
    records: list[dict[str, Any]],
    cat_id_to_label: dict[int, int],
    label_names: list[str],
    max_images: int,
    seed: int = 42,
    weak_names: tuple[str, ...] = WEAK_CLASS_NAMES,
    weak_image_fraction: float = 0.72,
) -> list[dict[str, Any]]:
    """Prefer images that contain the weak classes, without duplicating images.

    About ``weak_image_fraction`` of the subset is filled by round-robin over
    the weak classes. The rest is round-robin over the other foreground classes
    so shoes, dress, trousers, and jacket stay in the run.
    """
    if max_images is None or max_images >= len(records):
        return list(records)
    name_to_label = {name: index + 1 for index, name in enumerate(label_names)}
    weak_labels = [name_to_label[name] for name in weak_names if name in name_to_label]
    other_labels = [index + 1 for index, name in enumerate(label_names) if name not in weak_names]
    rng = random.Random(seed)
    by_class: dict[int, list[int]] = defaultdict(list)
    for index, row in enumerate(records):
        seen: set[int] = set()
        for ann in row["anns"]:
            cat_id = int(ann.get("category_id") or 0)
            if cat_id not in cat_id_to_label:
                continue
            label = cat_id_to_label[cat_id]
            if label not in seen:
                by_class[label].append(index)
                seen.add(label)
    for label in by_class:
        rng.shuffle(by_class[label])

    selected: list[int] = []
    used: set[int] = set()
    pointers = {label: 0 for label in by_class}

    def take_round_robin(labels: list[int], limit: int) -> None:
        if not labels:
            return
        order = list(labels)
        while len(selected) < limit:
            added = False
            for label in order:
                pool = by_class.get(label) or []
                while pointers.get(label, 0) < len(pool):
                    idx = pool[pointers[label]]
                    pointers[label] = pointers.get(label, 0) + 1
                    if idx in used:
                        continue
                    used.add(idx)
                    selected.append(idx)
                    added = True
                    break
                if len(selected) >= limit:
                    break
            if not added:
                break

    weak_limit = min(max_images, int(round(max_images * weak_image_fraction)))
    take_round_robin(weak_labels, weak_limit)
    take_round_robin(other_labels, max_images)
    if len(selected) < max_images:
        rest = [i for i in range(len(records)) if i not in used]
        rng.shuffle(rest)
        selected.extend(rest[: max_images - len(selected)])
    return [records[i] for i in selected[:max_images]]


class ClothingDetectionDataset(Dataset):
    """COCO instance dataset mapped to unified detector labels 1–15."""

    def __init__(
        self,
        image_dir: Path,
        annotation_path: Path,
        label_map: UnifiedLabelMap | None = None,
        *,
        max_images: int | None = None,
        skip_invalid: bool = True,
        subset_mode: str = "first",
        seed: int = 42,
        image_ids: set[int] | None = None,
        hflip_prob: float = 0.0,
    ) -> None:
        self.image_dir = Path(image_dir)
        self.annotation_path = Path(annotation_path)
        self.hflip_prob = float(hflip_prob)
        self.label_map = label_map or load_label_map()
        if len(self.label_map.detector_classes) != NUM_FOREGROUND:
            raise ValueError(
                f"taxonomy has {len(self.label_map.detector_classes)} classes, expected {NUM_FOREGROUND}"
            )
        coco = json.loads(self.annotation_path.read_text(encoding="utf-8"))
        self.total_images_in_json = len(coco.get("images") or [])
        self.total_annotations_in_json = len(coco.get("annotations") or [])
        self.cat_id_to_label = self._category_map(coco.get("categories") or [])
        self.label_names = list(self.label_map.detector_classes)
        anns_by_image: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for ann in coco.get("annotations") or []:
            anns_by_image[int(ann["image_id"])].append(ann)
        records = []
        diagnostics: list[str] = []
        for image in coco.get("images") or []:
            image_id = int(image["id"])
            anns = anns_by_image.get(image_id) or []
            if not anns:
                diagnostics.append(f"image {image_id}: no annotations")
                continue
            file_name = Path(str(image.get("file_name") or "")).name
            path = self.image_dir / file_name
            if not path.is_file():
                msg = f"image {image_id}: missing file {path}"
                if skip_invalid:
                    diagnostics.append(msg)
                    continue
                raise FileNotFoundError(msg)
            if image_ids is not None and image_id not in image_ids:
                continue
            records.append({"image": image, "path": path, "anns": anns})
            if (
                image_ids is None
                and max_images is not None
                and subset_mode == "first"
                and len(records) >= max_images
            ):
                break
        del coco
        if image_ids is not None:
            pass
        elif max_images is not None and subset_mode == "class_aware":
            records = class_aware_select(records, self.cat_id_to_label, max_images, seed=seed)
        elif max_images is not None and subset_mode == "weak_class":
            records = weak_class_select(
                records,
                self.cat_id_to_label,
                self.label_names,
                max_images,
                seed=seed,
            )
        self.records = records
        self.subset_mode = subset_mode
        self.diagnostics = diagnostics
        self.instance_diagnostics: list[str] = []
        if not self.records:
            raise RuntimeError(
                f"no usable images in {annotation_path} / {image_dir}. "
                f"diagnostics={diagnostics[:8]}"
            )

    def _category_map(self, categories: list[dict[str, Any]]) -> dict[int, int]:
        approved = list(self.label_map.detector_classes)
        mapping: dict[int, int] = {}
        for cat in categories:
            name = str(cat["name"])
            coco_id = int(cat["id"])
            if name not in approved:
                raise ValueError(f"unexpected COCO category {name!r} (id={coco_id})")
            label = self.label_map.class_id(name)
            if label != coco_id:
                # Convert whatever the JSON stored into taxonomy 1–15.
                mapping[coco_id] = label
            else:
                mapping[coco_id] = label
            if not (1 <= mapping[coco_id] <= NUM_FOREGROUND):
                raise ValueError(f"mapped label {mapping[coco_id]} out of range for {name}")
        return mapping

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
        row = self.records[index]
        image_meta = row["image"]
        path: Path = row["path"]
        with Image.open(path) as im:
            rgb = ImageOps.exif_transpose(im).convert("RGB")
            width, height = rgb.size
            image = torch.from_numpy(np.array(rgb, dtype=np.float32).transpose(2, 0, 1) / 255.0)
        expected_w, expected_h = int(image_meta["width"]), int(image_meta["height"])
        if width != expected_w or height != expected_h:
            raise AnnotationError(
                f"image {image_meta['id']}: file size {(width, height)} != JSON {(expected_w, expected_h)}"
            )
        boxes: list[list[float]] = []
        labels: list[int] = []
        masks: list[np.ndarray] = []
        areas: list[float] = []
        iscrowd: list[int] = []
        problems: list[str] = []
        for ann in row["anns"]:
            ann_id = int(ann.get("id") or -1)
            try:
                cat_id = int(ann["category_id"])
                if cat_id not in self.cat_id_to_label:
                    raise AnnotationError(f"unknown category_id {cat_id}")
                label = self.cat_id_to_label[cat_id]
                bbox = ann.get("bbox")
                if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
                    raise AnnotationError("bbox is not xywh")
                xyxy = coco_xywh_to_xyxy(list(bbox))
                mask = segmentation_to_mask(ann.get("segmentation"), height, width)
                xyxy, label, mask = validate_instance(
                    image_id=int(image_meta["id"]),
                    ann_id=ann_id,
                    box_xyxy=xyxy,
                    label=label,
                    mask=mask,
                    width=width,
                    height=height,
                )
            except AnnotationError as exc:
                problems.append(str(exc))
                continue
            boxes.append(xyxy)
            labels.append(label)
            masks.append(mask)
            areas.append(float(ann.get("area") or ((xyxy[2] - xyxy[0]) * (xyxy[3] - xyxy[1]))))
            iscrowd.append(int(ann.get("iscrowd") or 0))
        if problems:
            self.instance_diagnostics.extend(problems)
        if not boxes:
            raise AnnotationError(
                f"image {image_meta['id']} ({path.name}): no valid instances. " + "; ".join(problems)
            )
        n = len(boxes)
        if not (n == len(labels) == len(masks)):
            raise AnnotationError(f"image {image_meta['id']}: N mismatch boxes/labels/masks")
        labels_t = torch.tensor(labels, dtype=torch.int64)
        if int(labels_t.min()) < 1 or int(labels_t.max()) > NUM_FOREGROUND:
            raise AnnotationError(
                f"image {image_meta['id']}: labels {labels} not in 1..{NUM_FOREGROUND}"
            )
        boxes_t = torch.tensor(boxes, dtype=torch.float32)
        masks_t = torch.as_tensor(np.stack(masks, axis=0), dtype=torch.uint8)
        if self.hflip_prob > 0.0 and random.random() < self.hflip_prob:
            image = image.flip(-1)
            x1 = boxes_t[:, 0].clone()
            x2 = boxes_t[:, 2].clone()
            boxes_t[:, 0] = float(width) - x2
            boxes_t[:, 2] = float(width) - x1
            masks_t = masks_t.flip(-1)
        target = {
            "boxes": boxes_t,
            "labels": labels_t,
            "masks": masks_t,
            "image_id": torch.tensor([int(image_meta["id"])], dtype=torch.int64),
            "area": torch.tensor(areas, dtype=torch.float32),
            "iscrowd": torch.tensor(iscrowd, dtype=torch.int64),
        }
        return image, target


def detection_paths(root: Path | None = None) -> dict[str, Path]:
    base = Path(root) if root else DEFAULT_DATASET_ROOT
    return {
        "root": base,
        "train_images": base / "images" / "train",
        "val_images": base / "images" / "val",
        "test_images": base / "images" / "test",
        "train_ann": base / "annotations" / "instances_train.json",
        "val_ann": base / "annotations" / "instances_val.json",
        "test_ann": base / "annotations" / "instances_test.json",
    }
