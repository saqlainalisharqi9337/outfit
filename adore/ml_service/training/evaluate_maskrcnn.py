"""Evaluate a Mask R-CNN checkpoint on a capped validation subset.

Does not modify production inference. Full-split evaluation requires --allow-full.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torchvision.ops import box_iou

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parent
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from training.dataset import NUM_CLASSES, NUM_FOREGROUND, ClothingDetectionDataset, detection_paths
from training.label_map import load_label_map
from training.preview_maskrcnn import write_prediction_previews
from training.train_maskrcnn import (
    CHECKPOINT_DIR,
    apply_cpu_fast,
    build_maskrcnn,
    load_checkpoint,
    select_device,
)

PLANNED_METRICS = (
    "mAP@50",
    "mAP@50:95",
    "precision",
    "recall",
    "per-class AP",
    "confusion/error analysis",
)
DEFAULT_SCORE_THRESH = 0.5
DEFAULT_IOU_THRESH = 0.5
DEFAULT_PREVIEW_DIR = REPO_ROOT / "outputs" / "maskrcnn_preview"


def planned_metric_names() -> tuple[str, ...]:
    return PLANNED_METRICS


def _ap_from_recalls(precision: np.ndarray, recall: np.ndarray) -> float:
    if precision.size == 0:
        return 0.0
    mrec = np.concatenate(([0.0], recall, [1.0]))
    mpre = np.concatenate(([0.0], precision, [0.0]))
    for i in range(mpre.size - 1, 0, -1):
        mpre[i - 1] = max(mpre[i - 1], mpre[i])
    indices = np.where(mrec[1:] != mrec[:-1])[0]
    return float(np.sum((mrec[indices + 1] - mrec[indices]) * mpre[indices + 1]))


def class_average_precision(
    scores: list[float],
    matched: list[bool],
    n_gt: int,
) -> float:
    if n_gt <= 0:
        return 0.0
    if not scores:
        return 0.0
    order = np.argsort(-np.asarray(scores, dtype=np.float64))
    tp = np.zeros(len(scores), dtype=np.float64)
    fp = np.zeros(len(scores), dtype=np.float64)
    for i, idx in enumerate(order.tolist()):
        if matched[idx]:
            tp[i] = 1.0
        else:
            fp[i] = 1.0
    tp = np.cumsum(tp)
    fp = np.cumsum(fp)
    recall = tp / float(n_gt)
    precision = tp / np.maximum(tp + fp, 1e-9)
    return _ap_from_recalls(precision, recall)


def match_image(
    pred_boxes: torch.Tensor,
    pred_labels: torch.Tensor,
    pred_scores: torch.Tensor,
    gt_boxes: torch.Tensor,
    gt_labels: torch.Tensor,
    *,
    score_thresh: float,
    iou_thresh: float,
) -> dict[str, Any]:
    keep = pred_scores >= score_thresh
    pred_boxes = pred_boxes[keep]
    pred_labels = pred_labels[keep]
    pred_scores = pred_scores[keep]
    n_pred = int(pred_boxes.shape[0])
    n_gt = int(gt_boxes.shape[0])
    tp = 0
    ious: list[float] = []
    used = torch.zeros(n_gt, dtype=torch.bool)
    pred_matched = [False] * n_pred
    if n_pred and n_gt:
        ious_mat = box_iou(pred_boxes, gt_boxes)
        order = torch.argsort(pred_scores, descending=True)
        for pred_i in order.tolist():
            label = int(pred_labels[pred_i])
            row = ious_mat[pred_i]
            best_iou = -1.0
            best_gt = -1
            for gt_i in range(n_gt):
                if used[gt_i]:
                    continue
                if int(gt_labels[gt_i]) != label:
                    continue
                iou = float(row[gt_i])
                if iou > best_iou:
                    best_iou = iou
                    best_gt = gt_i
            if best_gt >= 0 and best_iou >= iou_thresh:
                used[best_gt] = True
                pred_matched[pred_i] = True
                tp += 1
                ious.append(best_iou)
    fp = n_pred - tp
    fn = n_gt - int(used.sum().item()) if n_gt else 0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "n_pred": n_pred,
        "n_gt": n_gt,
        "ious": ious,
        "pred_matched": pred_matched,
        "pred_labels": [int(v) for v in pred_labels.tolist()],
        "pred_scores": [float(v) for v in pred_scores.tolist()],
        "gt_labels": [int(v) for v in gt_labels.tolist()],
    }


def evaluate_model(
    model,
    dataset: ClothingDetectionDataset,
    device: torch.device,
    *,
    score_thresh: float = DEFAULT_SCORE_THRESH,
    iou_thresh: float = DEFAULT_IOU_THRESH,
    iou_thresholds: list[float] | None = None,
    on_image=None,
) -> dict[str, Any]:
    model.eval()
    names = list(dataset.label_names)
    iou_thresholds = iou_thresholds or [round(x, 2) for x in np.arange(0.5, 0.96, 0.05)]
    stats = {
        "tp": 0,
        "fp": 0,
        "fn": 0,
        "n_pred": 0,
        "n_gt": 0,
        "images": 0,
        "ious": [],
    }
    per_class = {
        name: {"tp": 0, "fp": 0, "fn": 0, "n_gt": 0, "scores": [], "matched": []}
        for name in names
    }
    ap50_store = {
        name: {"scores": [], "matched": [], "n_gt": 0} for name in names
    }
    ap_curve_store = {
        t: {name: {"scores": [], "matched": [], "n_gt": 0} for name in names} for t in iou_thresholds
    }

    for index in range(len(dataset)):
        image, target = dataset[index]
        with torch.no_grad():
            pred = model([image.to(device)])[0]
        gt_boxes = target["boxes"].to(device)
        gt_labels = target["labels"].to(device)
        matched = match_image(
            pred["boxes"],
            pred["labels"],
            pred["scores"],
            gt_boxes,
            gt_labels,
            score_thresh=score_thresh,
            iou_thresh=iou_thresh,
        )
        stats["images"] += 1
        stats["tp"] += matched["tp"]
        stats["fp"] += matched["fp"]
        stats["fn"] += matched["fn"]
        stats["n_pred"] += matched["n_pred"]
        stats["n_gt"] += matched["n_gt"]
        stats["ious"].extend(matched["ious"])
        if on_image is not None:
            on_image(index, image, target, pred)

        gt_count = defaultdict(int)
        for lab in matched["gt_labels"]:
            gt_count[names[lab - 1]] += 1
        pred_count = defaultdict(int)
        pred_tp = defaultdict(int)
        for lab, ok in zip(matched["pred_labels"], matched["pred_matched"]):
            name = names[lab - 1]
            pred_count[name] += 1
            if ok:
                pred_tp[name] += 1
        for name in names:
            n_gt = gt_count[name]
            tp = pred_tp[name]
            fp = pred_count[name] - tp
            fn = n_gt - tp
            per_class[name]["tp"] += tp
            per_class[name]["fp"] += fp
            per_class[name]["fn"] += fn
            per_class[name]["n_gt"] += n_gt

        # AP uses all returned detections (already score-filtered by the model)
        pred_boxes = pred["boxes"]
        pred_labels = pred["labels"]
        pred_scores = pred["scores"]
        for lab in target["labels"].tolist():
            ap50_store[names[int(lab) - 1]]["n_gt"] += 1
            for t in iou_thresholds:
                ap_curve_store[t][names[int(lab) - 1]]["n_gt"] += 1
        if pred_boxes.shape[0] and gt_boxes.shape[0]:
            ious_mat = box_iou(pred_boxes, gt_boxes)
        else:
            ious_mat = None
        used_50 = torch.zeros(int(gt_boxes.shape[0]), dtype=torch.bool, device=device)
        used_t = {
            t: torch.zeros(int(gt_boxes.shape[0]), dtype=torch.bool, device=device) for t in iou_thresholds
        }
        order = torch.argsort(pred_scores, descending=True) if pred_scores.numel() else torch.tensor([], dtype=torch.long)
        for pred_i in order.tolist():
            label = int(pred_labels[pred_i])
            if not (1 <= label <= len(names)):
                continue
            name = names[label - 1]
            score = float(pred_scores[pred_i])
            hit_50 = False
            if ious_mat is not None:
                row = ious_mat[pred_i]
                best_iou = -1.0
                best_gt = -1
                for gt_i in range(int(gt_boxes.shape[0])):
                    if used_50[gt_i]:
                        continue
                    if int(gt_labels[gt_i]) != label:
                        continue
                    iou = float(row[gt_i])
                    if iou > best_iou:
                        best_iou = iou
                        best_gt = gt_i
                if best_gt >= 0 and best_iou >= 0.5:
                    used_50[best_gt] = True
                    hit_50 = True
            ap50_store[name]["scores"].append(score)
            ap50_store[name]["matched"].append(hit_50)
            for t in iou_thresholds:
                hit = False
                if ious_mat is not None:
                    row = ious_mat[pred_i]
                    best_iou = -1.0
                    best_gt = -1
                    for gt_i in range(int(gt_boxes.shape[0])):
                        if used_t[t][gt_i]:
                            continue
                        if int(gt_labels[gt_i]) != label:
                            continue
                        iou = float(row[gt_i])
                        if iou > best_iou:
                            best_iou = iou
                            best_gt = gt_i
                    if best_gt >= 0 and best_iou >= t:
                        used_t[t][best_gt] = True
                        hit = True
                ap_curve_store[t][name]["scores"].append(score)
                ap_curve_store[t][name]["matched"].append(hit)
        for pred_i in range(int(pred_boxes.shape[0])):
            if gt_boxes.shape[0]:
                continue
            label = int(pred_labels[pred_i])
            if not (1 <= label <= len(names)):
                continue
            name = names[label - 1]
            score = float(pred_scores[pred_i])
            ap50_store[name]["scores"].append(score)
            ap50_store[name]["matched"].append(False)
            for t in iou_thresholds:
                ap_curve_store[t][name]["scores"].append(score)
                ap_curve_store[t][name]["matched"].append(False)

    precision = stats["tp"] / max(stats["tp"] + stats["fp"], 1)
    recall = stats["tp"] / max(stats["tp"] + stats["fn"], 1)
    mean_iou = float(np.mean(stats["ious"])) if stats["ious"] else 0.0
    per_class_out = {}
    ap50_values = []
    for name in names:
        row = per_class[name]
        p = row["tp"] / max(row["tp"] + row["fp"], 1)
        r = row["tp"] / max(row["tp"] + row["fn"], 1)
        ap50 = class_average_precision(ap50_store[name]["scores"], ap50_store[name]["matched"], ap50_store[name]["n_gt"])
        ap50_values.append(ap50)
        ap_curve = []
        for t in iou_thresholds:
            ap_curve.append(
                class_average_precision(
                    ap_curve_store[t][name]["scores"],
                    ap_curve_store[t][name]["matched"],
                    ap_curve_store[t][name]["n_gt"],
                )
            )
        per_class_out[name] = {
            "tp": row["tp"],
            "fp": row["fp"],
            "fn": row["fn"],
            "n_gt": row["n_gt"],
            "precision": p,
            "recall": r,
            "ap50": ap50,
            "ap50_95": float(np.mean(ap_curve)) if ap_curve else 0.0,
        }
    map50 = float(np.mean(ap50_values)) if ap50_values else 0.0
    map50_95 = float(np.mean([per_class_out[n]["ap50_95"] for n in names])) if names else 0.0
    return {
        "num_validation_images": stats["images"],
        "num_predictions": stats["n_pred"],
        "num_ground_truth": stats["n_gt"],
        "confidence_threshold": score_thresh,
        "iou_threshold": iou_thresh,
        "precision": precision,
        "recall": recall,
        "mean_iou": mean_iou,
        "map50": map50,
        "map50_95": map50_95,
        "per_class": per_class_out,
        "class_names": names,
    }


def print_metrics(metrics: dict[str, Any]) -> None:
    print("Validation images:", metrics["num_validation_images"])
    print("Predictions:", metrics["num_predictions"])
    print("Ground-truth instances:", metrics["num_ground_truth"])
    print("Confidence threshold:", metrics["confidence_threshold"])
    print("IoU threshold:", metrics["iou_threshold"])
    print(f"precision = {metrics['precision']:.4f}")
    print(f"recall = {metrics['recall']:.4f}")
    print(f"mean IoU (TP) = {metrics['mean_iou']:.4f}")
    print(f"mAP@50 = {metrics['map50']:.4f}")
    print(f"mAP@50:95 = {metrics['map50_95']:.4f}")
    print()
    print("Per-class results:")
    print(f"{'class':<12} {'n_gt':>5} {'tp':>5} {'fp':>5} {'fn':>5} {'P':>7} {'R':>7} {'AP50':>7}")
    for name in metrics["class_names"]:
        row = metrics["per_class"][name]
        print(
            f"{name:<12} {row['n_gt']:5d} {row['tp']:5d} {row['fp']:5d} {row['fn']:5d} "
            f"{row['precision']:7.3f} {row['recall']:7.3f} {row['ap50']:7.3f}"
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate a Mask R-CNN clothing checkpoint")
    parser.add_argument("--checkpoint", type=Path, default=CHECKPOINT_DIR / "best_model.pth")
    parser.add_argument("--max-images", type=int, default=50)
    parser.add_argument("--score-threshold", type=float, default=DEFAULT_SCORE_THRESH)
    parser.add_argument("--iou-threshold", type=float, default=DEFAULT_IOU_THRESH)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--preview-dir", type=Path, default=DEFAULT_PREVIEW_DIR)
    parser.add_argument("--preview-count", type=int, default=8)
    parser.add_argument("--allow-full", action="store_true")
    parser.add_argument("--no-preview", action="store_true")
    parser.add_argument("--metrics-json", type=Path, default=CHECKPOINT_DIR / "eval_metrics.json")
    parser.add_argument("--min-size", type=int, default=256)
    parser.add_argument("--max-size", type=int, default=320)
    parser.add_argument("--split", choices=("val", "test"), default="val")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    device = select_device(args.device)
    paths = detection_paths()
    image_dir = paths[f"{args.split}_images"]
    ann_path = paths[f"{args.split}_ann"]
    max_images = None if args.allow_full else args.max_images
    if max_images is None:
        print("Evaluating the entire split (--allow-full).")
    else:
        print(f"Evaluating at most {max_images} {args.split} images.")
    dataset = ClothingDetectionDataset(
        image_dir,
        ann_path,
        load_label_map(),
        max_images=max_images,
        skip_invalid=True,
    )
    if not args.checkpoint.is_file():
        print(f"Checkpoint not found: {args.checkpoint}")
        return 2
    ckpt_meta = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    cfg = ckpt_meta.get("config") or {}
    min_size = int(cfg.get("min_size") or args.min_size)
    max_size = int(cfg.get("max_size") or args.max_size)
    model = build_maskrcnn(NUM_CLASSES, pretrained=False, min_size=min_size, max_size=max_size, smoke_rpn=True)
    load_checkpoint(args.checkpoint, model, map_location=device)
    if device.type == "cpu":
        apply_cpu_fast(model)
    model.to(device)
    print(f"Loaded {args.checkpoint}")
    print(f"Device: {device}")
    metrics = evaluate_model(
        model,
        dataset,
        device,
        score_thresh=args.score_threshold,
        iou_thresh=args.iou_threshold,
    )
    print_metrics(metrics)
    args.metrics_json.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_json.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"Wrote metrics JSON: {args.metrics_json}")
    if not args.no_preview:
        written = write_prediction_previews(
            model,
            dataset,
            args.preview_dir,
            device,
            max_images=args.preview_count,
            score_thresh=min(args.score_threshold, 0.3),
        )
        print(f"Wrote {written} prediction previews to {args.preview_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
