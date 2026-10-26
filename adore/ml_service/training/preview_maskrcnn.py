"""Write a few Mask R-CNN dataset overlays. Does not modify source images."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parent
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from training.dataset import ClothingDetectionDataset, detection_paths
from training.label_map import load_label_map
from training.visualize_detection_dataset import PALETTE

DEFAULT_PREVIEW = REPO_ROOT / "evaluation_results" / "maskrcnn_pipeline_preview"
DEFAULT_PRED_PREVIEW = REPO_ROOT / "outputs" / "maskrcnn_preview"


def _font() -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", 16)
    except OSError:
        return ImageFont.load_default()


def render_overlay(image, target, label_names: list[str]) -> Image.Image:
    arr = (image.clamp(0, 1).permute(1, 2, 0).cpu().numpy() * 255.0).astype(np.uint8)
    rgb = Image.fromarray(arr).convert("RGBA")
    overlay = Image.new("RGBA", rgb.size, (0, 0, 0, 0))
    mask_rgba = np.zeros((rgb.size[1], rgb.size[0], 4), dtype=np.uint8)
    draw = ImageDraw.Draw(rgb)
    font = _font()
    boxes = target["boxes"].cpu()
    labels = target["labels"].cpu()
    masks = target["masks"].cpu()
    for i in range(int(labels.shape[0])):
        name = label_names[int(labels[i]) - 1]
        color = PALETTE.get(name, (255, 255, 255))
        instance = masks[i].numpy() > 0
        mask_rgba[instance, 0] = color[0]
        mask_rgba[instance, 1] = color[1]
        mask_rgba[instance, 2] = color[2]
        mask_rgba[instance, 3] = np.maximum(mask_rgba[instance, 3], 90)
        x1, y1, x2, y2 = (float(v) for v in boxes[i].tolist())
        draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
        draw.text((x1 + 2, max(0.0, y1 - 18.0)), name, fill=color, font=font)
    overlay = Image.fromarray(mask_rgba, mode="RGBA")
    return Image.alpha_composite(rgb, overlay).convert("RGB")


def render_predictions(image, pred: dict, label_names: list[str], score_thresh: float = 0.3) -> Image.Image:
    boxes = pred["boxes"].detach().cpu()
    labels = pred["labels"].detach().cpu()
    scores = pred["scores"].detach().cpu()
    masks = pred["masks"].detach().cpu()
    if masks.ndim == 4:
        masks = masks[:, 0]
    keep = scores >= score_thresh
    target = {
        "boxes": boxes[keep],
        "labels": labels[keep],
        "masks": (masks[keep] > 0.5).to(dtype=torch.uint8),
    }
    rgb = render_overlay(image, target, label_names)
    draw = ImageDraw.Draw(rgb)
    font = _font()
    kept_scores = scores[keep]
    kept_boxes = boxes[keep]
    kept_labels = labels[keep]
    for i in range(int(kept_labels.shape[0])):
        name = label_names[int(kept_labels[i]) - 1]
        x1, y1, _, _ = (float(v) for v in kept_boxes[i].tolist())
        draw.text(
            (x1 + 2, max(0.0, y1 - 18.0)),
            f"{name} {float(kept_scores[i]):.2f}",
            fill=PALETTE.get(name, (255, 255, 255)),
            font=font,
        )
    return rgb


def write_prediction_previews(
    model,
    dataset: ClothingDetectionDataset,
    dest_dir: Path,
    device,
    max_images: int = 8,
    score_thresh: float = 0.3,
) -> int:
    dest_dir.mkdir(parents=True, exist_ok=True)
    model.eval()
    written = 0
    for index in range(min(max_images, len(dataset))):
        image, _target = dataset[index]
        with torch.no_grad():
            pred = model([image.to(device)])[0]
        out = dest_dir / f"pred_{index:02d}_{dataset.records[index]['path'].stem}.jpg"
        render_predictions(image, pred, dataset.label_names, score_thresh=score_thresh).save(out, quality=92)
        written += 1
    return written


def write_previews(dataset: ClothingDetectionDataset, dest_dir: Path, max_images: int = 4) -> int:
    dest_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for index in range(min(max_images, len(dataset))):
        image, target = dataset[index]
        out = dest_dir / f"smoke_preview_{index:02d}_{dataset.records[index]['path'].stem}.jpg"
        render_overlay(image, target, dataset.label_names).save(out, quality=92)
        written += 1
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Save 3–5 Mask R-CNN dataset overlays")
    parser.add_argument("--max-images", type=int, default=4)
    parser.add_argument("--preview-dir", type=Path, default=DEFAULT_PREVIEW)
    parser.add_argument("--split", choices=("train", "val", "test"), default="train")
    args = parser.parse_args(argv)
    paths = detection_paths()
    dataset = ClothingDetectionDataset(
        paths[f"{args.split}_images"],
        paths[f"{args.split}_ann"],
        load_label_map(),
        max_images=args.max_images,
    )
    n = write_previews(dataset, args.preview_dir, max_images=args.max_images)
    print(f"wrote {n} previews to {args.preview_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
