"""Compare watch recall at score 0.5 under two proposal budgets.

Uses the frozen M4.11 checkpoint. Does not lower the score threshold and
does not write a new production checkpoint.
"""

from __future__ import annotations

import json
from pathlib import Path

import torch
from torchvision.ops import box_iou

from training.dataset import NUM_CLASSES, ClothingDetectionDataset, detection_paths
from training.label_map import load_label_map
from training.train_maskrcnn import build_maskrcnn, load_checkpoint, select_device

ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT = ROOT / "checkpoints" / "maskrcnn" / "m4_11" / "best_model.pth"
OUT = ROOT / "checkpoints" / "maskrcnn" / "m4_12" / "watch_proposal_ablation.json"
SCORE = 0.5
IOU = 0.5
CONFIGS = (
    {"name": "cpu_fast", "pre_nms": 100, "post_nms": 50, "detections": 20},
    {"name": "higher_capacity", "pre_nms": 400, "post_nms": 200, "detections": 100},
)


def scale_for(width: int, height: int) -> float:
    short = min(width, height)
    long = max(width, height)
    if short <= 0 or long <= 0:
        return 1.0
    return min(416.0 / short, 624.0 / long)


def apply_limits(model, pre_nms: int, post_nms: int, detections: int) -> None:
    model.rpn._pre_nms_top_n["testing"] = pre_nms
    model.rpn._post_nms_top_n["testing"] = post_nms
    model.roi_heads.detections_per_img = detections


def watch_ids(ann_path: Path, label_map) -> set[int]:
    coco = json.loads(ann_path.read_text(encoding="utf-8"))
    names = {int(cat["id"]): str(cat["name"]) for cat in coco["categories"]}
    watch_label = label_map.class_id("watch")
    ids: set[int] = set()
    for ann in coco["annotations"]:
        name = names.get(int(ann["category_id"]), "")
        if name == "watch" or int(ann["category_id"]) == watch_label:
            ids.add(int(ann["image_id"]))
    return ids


def main() -> int:
    device = select_device("cpu")
    paths = detection_paths()
    label_map = load_label_map()
    ids = watch_ids(paths["val_ann"], label_map)
    dataset = ClothingDetectionDataset(
        paths["val_images"],
        paths["val_ann"],
        label_map,
        skip_invalid=True,
        image_ids=ids,
    )
    watch_index = dataset.label_names.index("watch") + 1
    ckpt = torch.load(CHECKPOINT, map_location="cpu", weights_only=False)
    cfg = ckpt.get("config") or {}
    model = build_maskrcnn(
        NUM_CLASSES,
        pretrained=False,
        min_size=int(cfg.get("min_size") or 416),
        max_size=int(cfg.get("max_size") or 624),
        smoke_rpn=False,
    )
    load_checkpoint(CHECKPOINT, model, map_location=device)
    model.to(device)
    model.eval()
    print(f"Watch validation images: {len(dataset)}")
    results = []
    for spec in CONFIGS:
        apply_limits(model, spec["pre_nms"], spec["post_nms"], spec["detections"])
        tp = fp = fn = 0
        small_gt = small_tp = 0
        with torch.inference_mode():
            for index in range(len(dataset)):
                image, target = dataset[index]
                pred = model([image.to(device)])[0]
                keep = pred["scores"] >= SCORE
                boxes = pred["boxes"][keep]
                labels = pred["labels"][keep]
                scores = pred["scores"][keep]
                gt_boxes = target["boxes"]
                gt_labels = target["labels"]
                watch_gt = gt_labels == watch_index
                watch_pred = labels == watch_index
                gt_w = gt_boxes[watch_gt]
                pred_w = boxes[watch_pred]
                pred_s = scores[watch_pred]
                used = torch.zeros(int(gt_w.shape[0]), dtype=torch.bool)
                hit = 0
                if pred_w.numel() and gt_w.numel():
                    ious = box_iou(pred_w, gt_w)
                    order = torch.argsort(pred_s, descending=True)
                    for pred_i in order.tolist():
                        best_iou = -1.0
                        best_gt = -1
                        for gt_i in range(int(gt_w.shape[0])):
                            if used[gt_i]:
                                continue
                            iou = float(ious[pred_i, gt_i])
                            if iou > best_iou:
                                best_iou = iou
                                best_gt = gt_i
                        if best_gt >= 0 and best_iou >= IOU:
                            used[best_gt] = True
                            hit += 1
                image_tp = hit
                image_fp = int(pred_w.shape[0]) - hit
                image_fn = int(gt_w.shape[0]) - hit
                tp += image_tp
                fp += image_fp
                fn += image_fn
                width = int(image.shape[-1])
                height = int(image.shape[-2])
                factor = scale_for(width, height)
                for gt_i in range(int(gt_w.shape[0])):
                    x1, y1, x2, y2 = gt_w[gt_i].tolist()
                    if min(x2 - x1, y2 - y1) * factor < 16:
                        small_gt += 1
                        if bool(used[gt_i]):
                            small_tp += 1
                if (index + 1) % 20 == 0:
                    print(f"  {spec['name']} {index + 1}/{len(dataset)} tp={tp} fp={fp} fn={fn}")
        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        row = {
            **spec,
            "score_threshold": SCORE,
            "images": len(dataset),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": precision,
            "recall": recall,
            "small_gt_under_16px_at_416": small_gt,
            "small_tp": small_tp,
            "small_recall": small_tp / max(small_gt, 1),
        }
        results.append(row)
        print(json.dumps(row))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"checkpoint": str(CHECKPOINT), "configs": results}, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
