"""Official M4.12 validation pass plus the nine visual error cases.

Does not change the FastAPI checkpoint. One forward pass over the val split.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import torch
from PIL import Image, ImageDraw, ImageFont
from torchvision.ops import box_iou

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parent
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from training.analyze_maskrcnn_thresholds import error_analysis
from training.dataset import NUM_CLASSES, ClothingDetectionDataset, detection_paths
from training.evaluate_maskrcnn import evaluate_model
from training.label_map import load_label_map
from training.train_maskrcnn import apply_cpu_fast, build_maskrcnn, load_checkpoint, select_device

CASES = (
    "01_correct_shirt",
    "02_shirt_as_jacket",
    "03_correct_jacket",
    "04_jacket_as_shirt",
    "05_low_confidence_shirt",
    "06_correct_sweater",
    "07_missed_watch",
    "08_correct_watch",
    "09_false_positive_watch",
)


def _font():
    try:
        return ImageFont.truetype("arial.ttf", 16)
    except OSError:
        return ImageFont.load_default()


def _scale(width: int, height: int) -> float:
    short = min(width, height)
    long = max(width, height)
    if short <= 0 or long <= 0:
        return 1.0
    return min(416.0 / short, 624.0 / long)


def _save(dest: Path, image, pred_box, pred_name, score, gt_box, gt_name) -> None:
    arr = (image.clamp(0, 1).permute(1, 2, 0).cpu().numpy() * 255.0).astype("uint8")
    rgb = Image.fromarray(arr).convert("RGB")
    draw = ImageDraw.Draw(rgb)
    font = _font()
    if gt_box is not None:
        draw.rectangle(list(gt_box), outline=(40, 180, 70), width=3)
        draw.text((gt_box[0] + 2, max(0, gt_box[1] - 18)), f"gt {gt_name}", fill=(40, 180, 70), font=font)
    if pred_box is not None:
        draw.rectangle(list(pred_box), outline=(220, 40, 40), width=3)
        label = pred_name if score is None else f"{pred_name} {score:.2f}"
        draw.text((pred_box[0] + 2, max(0, pred_box[1] - 36)), label, fill=(220, 40, 40), font=font)
    dest.parent.mkdir(parents=True, exist_ok=True)
    rgb.save(dest, quality=92)


class CaseWriter:
    def __init__(self, dest: Path, names: list[str], records: list) -> None:
        self.dest = dest
        self.names = names
        self.records = records
        self.saved: set[str] = set()
        self.rows: list[dict] = []
        self.watch_small_gt = 0
        self.watch_small_tp = 0
        self.watch_fp = 0

    def __call__(self, index: int, image, target, pred) -> None:
        names = self.names
        boxes = pred["boxes"].detach().cpu()
        labels = pred["labels"].detach().cpu()
        scores = pred["scores"].detach().cpu()
        gt_boxes = target["boxes"].detach().cpu()
        gt_labels = target["labels"].detach().cpu()
        width = int(image.shape[-1])
        height = int(image.shape[-2])
        stem = self.records[index]["path"].stem if self.records else str(index)
        self.rows.append(
            {
                "boxes": boxes,
                "labels": labels,
                "scores": scores,
                "gt_boxes": gt_boxes,
                "gt_labels": gt_labels,
                "gt_areas": target["area"].detach().cpu(),
                "height": height,
                "width": width,
                "image_id": int(target["image_id"][0]),
                "stem": stem,
            }
        )
        watch_i = names.index("watch") + 1
        factor = _scale(width, height)
        n_pred = int(boxes.shape[0])
        n_gt = int(gt_boxes.shape[0])
        ious = box_iou(boxes, gt_boxes) if n_pred and n_gt else None

        def best_for(gt_i: int, same_only: bool):
            best = {"iou": -1.0, "score": 0.0, "pred_i": -1, "name": None}
            if ious is None:
                return best
            gt_name = names[int(gt_labels[gt_i]) - 1]
            for pred_i in range(n_pred):
                pred_name = names[int(labels[pred_i]) - 1]
                if same_only and pred_name != gt_name:
                    continue
                iou = float(ious[pred_i, gt_i])
                if iou > best["iou"]:
                    best = {
                        "iou": iou,
                        "score": float(scores[pred_i]),
                        "pred_i": pred_i,
                        "name": pred_name,
                    }
            return best

        for gt_i in range(n_gt):
            gt_name = names[int(gt_labels[gt_i]) - 1]
            same = best_for(gt_i, True)
            any_hit = best_for(gt_i, False)
            gt_box = [float(v) for v in gt_boxes[gt_i].tolist()]
            pred_box = None
            pred_name = None
            score = None
            if any_hit["pred_i"] >= 0:
                pred_box = [float(v) for v in boxes[any_hit["pred_i"]].tolist()]
                pred_name = any_hit["name"]
                score = any_hit["score"]
            case = None
            if gt_name == "shirt" and same["iou"] >= 0.5 and same["score"] >= 0.5:
                case = "01_correct_shirt"
                pred_box = [float(v) for v in boxes[same["pred_i"]].tolist()]
                pred_name, score = "shirt", same["score"]
            elif gt_name == "shirt" and any_hit["name"] == "jacket" and any_hit["iou"] >= 0.5:
                case = "02_shirt_as_jacket"
            elif gt_name == "jacket" and same["iou"] >= 0.5 and same["score"] >= 0.5:
                case = "03_correct_jacket"
                pred_box = [float(v) for v in boxes[same["pred_i"]].tolist()]
                pred_name, score = "jacket", same["score"]
            elif gt_name == "jacket" and any_hit["name"] == "shirt" and any_hit["iou"] >= 0.5:
                case = "04_jacket_as_shirt"
            elif gt_name == "shirt" and same["iou"] >= 0.5 and same["score"] < 0.5:
                case = "05_low_confidence_shirt"
                pred_box = [float(v) for v in boxes[same["pred_i"]].tolist()]
                pred_name, score = "shirt", same["score"]
            elif gt_name == "sweater" and same["iou"] >= 0.5 and same["score"] >= 0.5:
                case = "06_correct_sweater"
                pred_box = [float(v) for v in boxes[same["pred_i"]].tolist()]
                pred_name, score = "sweater", same["score"]
            elif gt_name == "watch" and any_hit["iou"] < 0.1:
                case = "07_missed_watch"
                pred_box, pred_name, score = None, None, None
            elif gt_name == "watch" and same["iou"] >= 0.5 and same["score"] >= 0.5:
                case = "08_correct_watch"
                pred_box = [float(v) for v in boxes[same["pred_i"]].tolist()]
                pred_name, score = "watch", same["score"]
            if case and case not in self.saved:
                self.saved.add(case)
                _save(self.dest / f"{case}.jpg", image, pred_box, pred_name, score, gt_box, gt_name)
            if gt_name == "watch":
                x1, y1, x2, y2 = gt_box
                if min(x2 - x1, y2 - y1) * factor < 16:
                    self.watch_small_gt += 1
                    if same["iou"] >= 0.5 and same["score"] >= 0.5:
                        self.watch_small_tp += 1

        used = set()
        if ious is not None:
            for pred_i in range(n_pred):
                if names[int(labels[pred_i]) - 1] != "watch" or float(scores[pred_i]) < 0.5:
                    continue
                best_gt = -1
                best_iou = -1.0
                for gt_i in range(n_gt):
                    if int(gt_labels[gt_i]) != watch_i or gt_i in used:
                        continue
                    iou = float(ious[pred_i, gt_i])
                    if iou > best_iou:
                        best_iou = iou
                        best_gt = gt_i
                if best_gt >= 0 and best_iou >= 0.5:
                    used.add(best_gt)
                else:
                    self.watch_fp += 1
                    if "09_false_positive_watch" not in self.saved:
                        self.saved.add("09_false_positive_watch")
                        gt_box = None
                        gt_name = "none"
                        if n_gt:
                            gt_box = [float(v) for v in gt_boxes[0].tolist()]
                            gt_name = names[int(gt_labels[0]) - 1]
                        _save(
                            self.dest / "09_false_positive_watch.jpg",
                            image,
                            [float(v) for v in boxes[pred_i].tolist()],
                            "watch",
                            float(scores[pred_i]),
                            gt_box,
                            gt_name,
                        )


def main() -> int:
    checkpoint = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / "checkpoints" / "maskrcnn" / "m4_12" / "best_model.pth"
    out_dir = REPO_ROOT / "checkpoints" / "maskrcnn" / "m4_12"
    preview = REPO_ROOT / "outputs" / "maskrcnn_m4_12" / "error_analysis"
    device = select_device("cpu")
    paths = detection_paths()
    dataset = ClothingDetectionDataset(
        paths["val_images"],
        paths["val_ann"],
        load_label_map(),
        skip_invalid=True,
    )
    ckpt = torch.load(checkpoint, map_location="cpu", weights_only=False)
    cfg = ckpt.get("config") or {}
    model = build_maskrcnn(
        NUM_CLASSES,
        pretrained=False,
        min_size=int(cfg.get("min_size") or 416),
        max_size=int(cfg.get("max_size") or 624),
        smoke_rpn=True,
    )
    load_checkpoint(checkpoint, model, map_location=device)
    if device.type == "cpu":
        apply_cpu_fast(model)
    model.to(device)
    writer = CaseWriter(preview, list(dataset.label_names), dataset.records)
    print(f"Evaluating {len(dataset)} val images from {checkpoint}")
    metrics = evaluate_model(model, dataset, device, score_thresh=0.5, iou_thresh=0.5, on_image=writer)
    analysis = error_analysis(writer.rows, list(dataset.label_names))
    payload = {
        "checkpoint": str(checkpoint),
        "epoch": ckpt.get("epoch"),
        "val_loss": ckpt.get("val_loss"),
        "metrics": metrics,
        "confusion_focus": analysis.get("focus_pairs"),
        "per_gt": {
            name: analysis["per_class"][name]
            for name in ("shirt", "jacket", "sweater", "watch")
        },
        "watch_false_positives_at_0.5": writer.watch_fp,
        "watch_small_gt": writer.watch_small_gt,
        "watch_small_tp": writer.watch_small_tp,
        "visuals": sorted(writer.saved),
        "visual_dir": str(preview),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / "eval_metrics.json"
    dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {dest}")
    print("Visuals:", sorted(writer.saved))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
