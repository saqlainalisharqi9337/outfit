"""M4.7 threshold, confidence, and confusion study.

Uses a frozen Mask R-CNN checkpoint. Does not train, and is not imported by FastAPI.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
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

from training.dataset import ClothingDetectionDataset, detection_paths
from training.evaluate_maskrcnn import class_average_precision, match_image
from training.label_map import load_label_map
from training.preview_maskrcnn import write_prediction_previews
from training.train_maskrcnn import (
    apply_cpu_fast,
    build_maskrcnn,
    load_checkpoint,
    select_device,
)

DEFAULT_THRESHOLDS = (0.50, 0.40, 0.30, 0.20, 0.10)
DEFAULT_IOU = 0.5
ACCESSORY_CLASSES = ("bag", "hat", "belt", "scarf", "watch", "sunglasses")
WEAK_FOCUS = ("shirt", "jacket", "bag", "hat", "belt", "scarf", "watch", "sunglasses")
CONFUSION_FOCUS = (
    ("shirt", "jacket"),
    ("shirt", "dress"),
    ("jacket", "shirt"),
    ("shorts", "skirt"),
    ("skirt", "shorts"),
    ("trousers", "shirt"),
    ("dress", "shirt"),
    ("bag", "hat"),
    ("bag", "belt"),
    ("bag", "scarf"),
    ("hat", "bag"),
    ("hat", "scarf"),
    ("belt", "watch"),
    ("belt", "scarf"),
    ("scarf", "belt"),
    ("scarf", "hat"),
    ("watch", "belt"),
    ("watch", "sunglasses"),
    ("sunglasses", "watch"),
    ("sunglasses", "hat"),
)


def collect_detections(model, dataset: ClothingDetectionDataset, device: torch.device) -> list[dict[str, Any]]:
    model.eval()
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    total = len(dataset)
    for index in range(total):
        image, target = dataset[index]
        with torch.no_grad():
            pred = model([image.to(device)])[0]
        if index == 0 or (index + 1) % 100 == 0 or index + 1 == total:
            elapsed = time.perf_counter() - started
            print(f"  infer {index + 1}/{total}  elapsed_s={elapsed:.1f}", flush=True)
        h, w = int(image.shape[1]), int(image.shape[2])
        rows.append(
            {
                "index": index,
                "stem": dataset.records[index]["path"].stem,
                "image_id": int(target["image_id"].item()),
                "height": h,
                "width": w,
                "boxes": pred["boxes"].detach().cpu(),
                "labels": pred["labels"].detach().cpu(),
                "scores": pred["scores"].detach().cpu(),
                "gt_boxes": target["boxes"].cpu(),
                "gt_labels": target["labels"].cpu(),
                "gt_areas": target["area"].cpu(),
            }
        )
    return rows


def metrics_from_detections(
    rows: list[dict[str, Any]],
    names: list[str],
    *,
    score_thresh: float,
    iou_thresh: float = DEFAULT_IOU,
    filter_ap: bool = True,
) -> dict[str, Any]:
    """Same matching rules as evaluate_model, optionally restricting AP to score_thresh."""
    iou_thresholds = [round(x, 2) for x in np.arange(0.5, 0.96, 0.05)]
    stats = {"tp": 0, "fp": 0, "fn": 0, "n_pred": 0, "n_gt": 0, "images": 0, "ious": []}
    per_class = {name: {"tp": 0, "fp": 0, "fn": 0, "n_gt": 0} for name in names}
    ap50_store = {name: {"scores": [], "matched": [], "n_gt": 0} for name in names}
    ap_curve_store = {t: {name: {"scores": [], "matched": [], "n_gt": 0} for name in names} for t in iou_thresholds}

    for row in rows:
        pred_boxes = row["boxes"]
        pred_labels = row["labels"]
        pred_scores = row["scores"]
        gt_boxes = row["gt_boxes"]
        gt_labels = row["gt_labels"]
        matched = match_image(
            pred_boxes,
            pred_labels,
            pred_scores,
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

        gt_count: dict[str, int] = defaultdict(int)
        for lab in matched["gt_labels"]:
            gt_count[names[lab - 1]] += 1
        pred_count: dict[str, int] = defaultdict(int)
        pred_tp: dict[str, int] = defaultdict(int)
        for lab, ok in zip(matched["pred_labels"], matched["pred_matched"]):
            name = names[lab - 1]
            pred_count[name] += 1
            if ok:
                pred_tp[name] += 1
        for name in names:
            n_gt = gt_count[name]
            tp = pred_tp[name]
            per_class[name]["tp"] += tp
            per_class[name]["fp"] += pred_count[name] - tp
            per_class[name]["fn"] += n_gt - tp
            per_class[name]["n_gt"] += n_gt

        keep = pred_scores >= score_thresh if filter_ap else torch.ones_like(pred_scores, dtype=torch.bool)
        ap_boxes = pred_boxes[keep]
        ap_labels = pred_labels[keep]
        ap_scores = pred_scores[keep]
        for lab in gt_labels.tolist():
            ap50_store[names[int(lab) - 1]]["n_gt"] += 1
            for t in iou_thresholds:
                ap_curve_store[t][names[int(lab) - 1]]["n_gt"] += 1
        ious_mat = box_iou(ap_boxes, gt_boxes) if ap_boxes.shape[0] and gt_boxes.shape[0] else None
        used_50 = torch.zeros(int(gt_boxes.shape[0]), dtype=torch.bool)
        used_t = {t: torch.zeros(int(gt_boxes.shape[0]), dtype=torch.bool) for t in iou_thresholds}
        order = torch.argsort(ap_scores, descending=True) if ap_scores.numel() else torch.tensor([], dtype=torch.long)
        for pred_i in order.tolist():
            label = int(ap_labels[pred_i])
            if not (1 <= label <= len(names)):
                continue
            name = names[label - 1]
            score = float(ap_scores[pred_i])
            hit_50 = False
            if ious_mat is not None:
                row_iou = ious_mat[pred_i]
                best_iou = -1.0
                best_gt = -1
                for gt_i in range(int(gt_boxes.shape[0])):
                    if used_50[gt_i] or int(gt_labels[gt_i]) != label:
                        continue
                    iou = float(row_iou[gt_i])
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
                    row_iou = ious_mat[pred_i]
                    best_iou = -1.0
                    best_gt = -1
                    for gt_i in range(int(gt_boxes.shape[0])):
                        if used_t[t][gt_i] or int(gt_labels[gt_i]) != label:
                            continue
                        iou = float(row_iou[gt_i])
                        if iou > best_iou:
                            best_iou = iou
                            best_gt = gt_i
                    if best_gt >= 0 and best_iou >= t:
                        used_t[t][best_gt] = True
                        hit = True
                ap_curve_store[t][name]["scores"].append(score)
                ap_curve_store[t][name]["matched"].append(hit)
        if int(gt_boxes.shape[0]) == 0:
            for pred_i in range(int(ap_boxes.shape[0])):
                label = int(ap_labels[pred_i])
                if not (1 <= label <= len(names)):
                    continue
                name = names[label - 1]
                score = float(ap_scores[pred_i])
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
        ap_curve = [
            class_average_precision(
                ap_curve_store[t][name]["scores"],
                ap_curve_store[t][name]["matched"],
                ap_curve_store[t][name]["n_gt"],
            )
            for t in iou_thresholds
        ]
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
    return {
        "num_validation_images": stats["images"],
        "num_predictions": stats["n_pred"],
        "num_ground_truth": stats["n_gt"],
        "tp": stats["tp"],
        "fp": stats["fp"],
        "fn": stats["fn"],
        "confidence_threshold": score_thresh,
        "iou_threshold": iou_thresh,
        "precision": precision,
        "recall": recall,
        "mean_iou": mean_iou,
        "map50": float(np.mean(ap50_values)) if ap50_values else 0.0,
        "map50_95": float(np.mean([per_class_out[n]["ap50_95"] for n in names])) if names else 0.0,
        "per_class": per_class_out,
        "class_names": names,
    }


def confidence_stats(rows: list[dict[str, Any]], names: list[str], *, min_score: float = 0.0) -> dict[str, dict[str, float | int]]:
    buckets: dict[str, list[float]] = {name: [] for name in names}
    for row in rows:
        for label, score in zip(row["labels"].tolist(), row["scores"].tolist()):
            value = float(score)
            if value < min_score:
                continue
            if 1 <= int(label) <= len(names):
                buckets[names[int(label) - 1]].append(value)
    out: dict[str, dict[str, float | int]] = {}
    for name in names:
        values = buckets[name]
        if not values:
            out[name] = {
                "n_pred": 0,
                "min": None,
                "max": None,
                "mean": None,
                "median": None,
                "n_below_0_5": 0,
                "n_at_or_above_0_5": 0,
            }
            continue
        arr = np.asarray(values, dtype=np.float64)
        out[name] = {
            "n_pred": int(arr.size),
            "min": float(arr.min()),
            "max": float(arr.max()),
            "mean": float(arr.mean()),
            "median": float(np.median(arr)),
            "n_below_0_5": int(np.sum(arr < 0.5)),
            "n_at_or_above_0_5": int(np.sum(arr >= 0.5)),
        }
    return out


def size_bin(rel_area: float) -> str:
    if rel_area < 0.01:
        return "tiny(<1%)"
    if rel_area < 0.05:
        return "small(1-5%)"
    if rel_area < 0.15:
        return "medium(5-15%)"
    return "large(>15%)"


def error_analysis(rows: list[dict[str, Any]], names: list[str], *, iou_thresh: float = DEFAULT_IOU) -> dict[str, Any]:
    """Per-GT diagnosis: low-confidence, wrong-class, poor localization, or missed."""
    per_class = {
        name: {
            "n_gt": 0,
            "correct_high_conf": 0,
            "correct_low_conf": 0,
            "wrong_class": 0,
            "poor_localization": 0,
            "missed": 0,
            "wrong_class_to": defaultdict(int),
            "size_bins": defaultdict(lambda: {"n_gt": 0, "correct": 0, "wrong_class": 0, "poor_localization": 0, "missed": 0}),
        }
        for name in names
    }
    confusion = {src: {dst: 0 for dst in names} for src in names}
    pair_counts = {f"{a}->{b}": 0 for a, b in CONFUSION_FOCUS}
    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        pred_boxes = row["boxes"]
        pred_labels = row["labels"]
        pred_scores = row["scores"]
        gt_boxes = row["gt_boxes"]
        gt_labels = row["gt_labels"]
        gt_areas = row["gt_areas"]
        image_area = float(row["height"] * row["width"]) or 1.0
        n_gt = int(gt_boxes.shape[0])
        n_pred = int(pred_boxes.shape[0])
        ious_mat = box_iou(pred_boxes, gt_boxes) if n_pred and n_gt else None
        for gt_i in range(n_gt):
            gt_name = names[int(gt_labels[gt_i]) - 1]
            rel = float(gt_areas[gt_i]) / image_area
            bin_name = size_bin(rel)
            bucket = per_class[gt_name]
            bucket["n_gt"] += 1
            bucket["size_bins"][bin_name]["n_gt"] += 1
            best_same = {"iou": -1.0, "score": 0.0, "pred_i": -1}
            best_any = {"iou": -1.0, "score": 0.0, "pred_i": -1, "name": None}
            if ious_mat is not None:
                for pred_i in range(n_pred):
                    iou = float(ious_mat[pred_i, gt_i])
                    score = float(pred_scores[pred_i])
                    pred_name = names[int(pred_labels[pred_i]) - 1]
                    if iou > best_any["iou"]:
                        best_any = {"iou": iou, "score": score, "pred_i": pred_i, "name": pred_name}
                    if pred_name == gt_name and iou > best_same["iou"]:
                        best_same = {"iou": iou, "score": score, "pred_i": pred_i}
            detail = {
                "image_id": row["image_id"],
                "stem": row["stem"],
                "gt": gt_name,
                "pred": best_any["name"],
                "score": best_any["score"],
                "iou": best_any["iou"],
                "rel_area": rel,
                "size_bin": bin_name,
            }
            if best_same["iou"] >= iou_thresh:
                if best_same["score"] >= 0.5:
                    bucket["correct_high_conf"] += 1
                    bucket["size_bins"][bin_name]["correct"] += 1
                    kind = "correct_high_conf"
                else:
                    bucket["correct_low_conf"] += 1
                    bucket["size_bins"][bin_name]["correct"] += 1
                    kind = "correct_low_conf"
                    if len(examples[f"low_conf:{gt_name}"]) < 8:
                        examples[f"low_conf:{gt_name}"].append(
                            {**detail, "pred": gt_name, "score": best_same["score"], "iou": best_same["iou"]}
                        )
            elif best_any["iou"] >= iou_thresh and best_any["name"] != gt_name:
                bucket["wrong_class"] += 1
                bucket["wrong_class_to"][best_any["name"]] += 1
                bucket["size_bins"][bin_name]["wrong_class"] += 1
                confusion[gt_name][best_any["name"]] += 1
                key = f"{gt_name}->{best_any['name']}"
                if key in pair_counts:
                    pair_counts[key] += 1
                kind = "wrong_class"
                if len(examples[f"wrong:{key}"]) < 8:
                    examples[f"wrong:{key}"].append(detail)
            elif best_any["iou"] >= 0.1:
                bucket["poor_localization"] += 1
                bucket["size_bins"][bin_name]["poor_localization"] += 1
                kind = "poor_localization"
                if len(examples[f"loc:{gt_name}"]) < 5:
                    examples[f"loc:{gt_name}"].append(detail)
            else:
                bucket["missed"] += 1
                bucket["size_bins"][bin_name]["missed"] += 1
                kind = "missed"
                if gt_name in ACCESSORY_CLASSES and len(examples[f"missed:{gt_name}"]) < 8:
                    examples[f"missed:{gt_name}"].append(detail)
            _ = kind

    serial_class = {}
    for name in names:
        row = per_class[name]
        serial_class[name] = {
            "n_gt": row["n_gt"],
            "correct_high_conf": row["correct_high_conf"],
            "correct_low_conf": row["correct_low_conf"],
            "wrong_class": row["wrong_class"],
            "poor_localization": row["poor_localization"],
            "missed": row["missed"],
            "wrong_class_to": dict(row["wrong_class_to"]),
            "size_bins": {k: dict(v) for k, v in row["size_bins"].items()},
        }
    return {
        "per_class": serial_class,
        "confusion": confusion,
        "focus_pairs": pair_counts,
        "examples": dict(examples),
    }


def diagnosis_label(row: dict[str, Any]) -> str:
    n = max(row["n_gt"], 1)
    low = row["correct_low_conf"] / n
    high = row["correct_high_conf"] / n
    wrong = row["wrong_class"] / n
    loc = row["poor_localization"] / n
    miss = row["missed"] / n
    if miss >= 0.70 and low < 0.10 and wrong < 0.10:
        return "C. completely missed"
    if low >= 0.15 and low >= wrong and low >= miss * 0.5:
        return "A. detected but below confidence 0.5"
    if wrong >= 0.15 and wrong >= low:
        return "B. detected as the wrong clothing class"
    if loc >= 0.20:
        return "localization/segmentation (IoU below 0.5)"
    if high >= 0.40:
        return "mostly detected at or above 0.5"
    return "mixed / weak signal"


def print_sweep(rows_metrics: list[dict[str, Any]]) -> None:
    print("Threshold sweep (IoU=0.5; AP uses detections at or above the score threshold):")
    print(
        f"{'score':>6} {'n_pred':>7} {'n_gt':>5} {'TP':>5} {'FP':>5} {'FN':>5} "
        f"{'P':>7} {'R':>7} {'mAP50':>7} {'mAP5095':>8} {'mIoU':>7}"
    )
    for metrics in rows_metrics:
        print(
            f"{metrics['confidence_threshold']:6.2f} {metrics['num_predictions']:7d} "
            f"{metrics['num_ground_truth']:5d} {metrics['tp']:5d} {metrics['fp']:5d} {metrics['fn']:5d} "
            f"{metrics['precision']:7.3f} {metrics['recall']:7.3f} {metrics['map50']:7.3f} "
            f"{metrics['map50_95']:8.3f} {metrics['mean_iou']:7.3f}"
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="M4.7 Mask R-CNN threshold and error study")
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--max-images", type=int, default=150)
    parser.add_argument("--iou-threshold", type=float, default=DEFAULT_IOU)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--split", choices=("val", "test"), default="val")
    parser.add_argument(
        "--out-json",
        type=Path,
        default=REPO_ROOT / "checkpoints" / "maskrcnn" / "m4_6" / "m4_7_threshold_study.json",
    )
    parser.add_argument("--preview-dir", type=Path, default=REPO_ROOT / "outputs" / "maskrcnn_m4_7")
    parser.add_argument("--preview-count", type=int, default=8)
    parser.add_argument("--no-preview", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.checkpoint.is_file():
        print(f"Checkpoint not found: {args.checkpoint}")
        return 2
    device = select_device(args.device)
    paths = detection_paths()
    dataset = ClothingDetectionDataset(
        paths[f"{args.split}_images"],
        paths[f"{args.split}_ann"],
        load_label_map(),
        max_images=args.max_images,
        skip_invalid=True,
    )
    ckpt_meta = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    cfg = ckpt_meta.get("config") or {}
    print(f"Loaded {args.checkpoint}")
    print(f"checkpoint epoch={ckpt_meta.get('epoch')} best={ckpt_meta.get('best')} val_loss={ckpt_meta.get('val_loss')}")
    print(f"Device: {device}")
    print(f"Eval images: {len(dataset)}")
    model = build_maskrcnn(
        int(ckpt_meta.get("num_classes") or 16),
        pretrained=False,
        min_size=int(cfg.get("min_size") or 256),
        max_size=int(cfg.get("max_size") or 320),
        smoke_rpn=True,
    )
    load_checkpoint(args.checkpoint, model, map_location=device)
    if device.type == "cpu":
        apply_cpu_fast(model)
    model.to(device)

    names = list(dataset.label_names)
    infer_started = time.perf_counter()
    detections = collect_detections(model, dataset, device)
    inference_seconds = time.perf_counter() - infer_started
    print(f"inference_seconds={inference_seconds:.1f} images={len(dataset)} device={device}")
    ranking = metrics_from_detections(
        detections, names, score_thresh=0.0, iou_thresh=args.iou_threshold, filter_ap=False
    )
    print()
    print("Ranking AP using all model detections (same rule as M4.6 AP):")
    print(f"  mAP@50={ranking['map50']:.4f}  mAP@50:95={ranking['map50_95']:.4f}  n_pred_all={ranking['num_predictions']}")
    print()

    sweep = []
    for thresh in DEFAULT_THRESHOLDS:
        metrics = metrics_from_detections(
            detections, names, score_thresh=thresh, iou_thresh=args.iou_threshold, filter_ap=True
        )
        sweep.append(metrics)
        print(f"--- score {thresh:.2f} ---")
        print(
            f"predictions={metrics['num_predictions']} GT={metrics['num_ground_truth']} "
            f"TP={metrics['tp']} FP={metrics['fp']} FN={metrics['fn']}"
        )
        print(
            f"P={metrics['precision']:.4f} R={metrics['recall']:.4f} "
            f"mAP@50={metrics['map50']:.4f} mAP@50:95={metrics['map50_95']:.4f} "
            f"meanIoU={metrics['mean_iou']:.4f}"
        )
        print(f"{'class':<12} {'n_gt':>5} {'tp':>5} {'fp':>5} {'fn':>5} {'P':>7} {'R':>7} {'AP50':>7}")
        for name in names:
            row = metrics["per_class"][name]
            print(
                f"{name:<12} {row['n_gt']:5d} {row['tp']:5d} {row['fp']:5d} {row['fn']:5d} "
                f"{row['precision']:7.3f} {row['recall']:7.3f} {row['ap50']:7.3f}"
            )
        print()
    print_sweep(sweep)

    conf = confidence_stats(detections, names)
    print()
    print("Confidence statistics (all model detections):")
    print(f"{'class':<12} {'n':>5} {'min':>7} {'max':>7} {'mean':>7} {'median':>7} {'<0.5':>6} {'>=0.5':>6}")
    for name in names:
        row = conf[name]
        if row["n_pred"] == 0:
            print(f"{name:<12} {0:5d} {'—':>7} {'—':>7} {'—':>7} {'—':>7} {0:6d} {0:6d}")
            continue
        print(
            f"{name:<12} {row['n_pred']:5d} {row['min']:7.3f} {row['max']:7.3f} "
            f"{row['mean']:7.3f} {row['median']:7.3f} {row['n_below_0_5']:6d} {row['n_at_or_above_0_5']:6d}"
        )

    errors = error_analysis(detections, names, iou_thresh=args.iou_threshold)
    print()
    print("Per-GT diagnosis (best overlapping detection, IoU 0.5 / low-conf if score<0.5):")
    print(
        f"{'class':<12} {'n_gt':>5} {'hi>=0.5':>8} {'lo<0.5':>7} {'wrong':>6} {'loc':>5} {'miss':>5}  diagnosis"
    )
    diagnoses = {}
    for name in names:
        row = errors["per_class"][name]
        label = diagnosis_label(row)
        diagnoses[name] = label
        print(
            f"{name:<12} {row['n_gt']:5d} {row['correct_high_conf']:8d} {row['correct_low_conf']:7d} "
            f"{row['wrong_class']:6d} {row['poor_localization']:5d} {row['missed']:5d}  {label}"
        )
    print()
    print("Focused confusion counts (GT IoU>=0.5 onto a different class):")
    for key, count in errors["focus_pairs"].items():
        if count:
            print(f"  {key}: {count}")

    payload = {
        "checkpoint": str(args.checkpoint),
        "checkpoint_epoch": ckpt_meta.get("epoch"),
        "checkpoint_best": ckpt_meta.get("best"),
        "checkpoint_val_loss": ckpt_meta.get("val_loss"),
        "num_images": len(dataset),
        "device": str(device),
        "inference_seconds": inference_seconds,
        "iou_threshold": args.iou_threshold,
        "ranking_ap": {
            "map50": ranking["map50"],
            "map50_95": ranking["map50_95"],
            "num_predictions": ranking["num_predictions"],
            "per_class_ap50": {name: ranking["per_class"][name]["ap50"] for name in names},
        },
        "thresholds": sweep,
        "confidence": conf,
        "error_analysis": errors,
        "diagnoses": diagnoses,
        "class_names": names,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {args.out_json}")

    if not args.no_preview:
        written = write_prediction_previews(
            model,
            dataset,
            args.preview_dir,
            device,
            max_images=args.preview_count,
            score_thresh=0.1,
        )
        print(f"Wrote {written} score>=0.1 previews to {args.preview_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
