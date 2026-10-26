"""Classify one image or a folder with the trained 4-class garment model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
import torch.nn.functional as F
from PIL import Image

from .config import CLASS_ORDER, DEFAULT_DATASET, EXTS, LABELS_NAME, MODEL_NAME, MODELS_DIR
from .dataset import build_transforms
from .model import build_model


def load_classifier(checkpoint: Path, device: torch.device):
    ckpt = torch.load(checkpoint, map_location=device, weights_only=False)
    classes = ckpt.get("classes", list(CLASS_ORDER))
    backbone = ckpt.get("backbone", "resnet18")
    model = build_model(backbone, num_classes=len(classes), pretrained=False)
    model.load_state_dict(ckpt["model_state"])
    model.to(device)
    model.eval()
    labels_path = MODELS_DIR / LABELS_NAME
    meta = {}
    if labels_path.is_file():
        meta = json.loads(labels_path.read_text(encoding="utf-8"))
    return model, classes, meta


@torch.no_grad()
def predict_image(
    model,
    classes: list[str],
    image_path: Path,
    device: torch.device,
    transform,
) -> dict:
    with Image.open(image_path) as img:
        rgb = img.convert("RGB")
    tensor = transform(rgb).unsqueeze(0).to(device)
    probs = F.softmax(model(tensor), dim=1)[0]
    conf, idx = torch.max(probs, dim=0)
    ranking = sorted(
        (
            {"label": classes[i], "score": float(probs[i])}
            for i in range(len(classes))
        ),
        key=lambda row: -row["score"],
    )
    return {
        "path": str(image_path),
        "label": classes[int(idx)],
        "confidence": float(conf),
        "ranking": ranking,
    }


def iter_images(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(
        p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in EXTS
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path, help="Image file or folder")
    parser.add_argument("--checkpoint", type=Path, default=MODELS_DIR / MODEL_NAME)
    parser.add_argument("--cpu", action="store_true")
    parser.add_argument("--min-confidence", type=float, default=0.0)
    args = parser.parse_args()

    if not args.checkpoint.is_file():
        raise SystemExit(f"Missing checkpoint: {args.checkpoint}. Train first.")
    if not args.path.exists():
        raise SystemExit(f"Path not found: {args.path}")

    device = torch.device(
        "cuda" if torch.cuda.is_available() and not args.cpu else "cpu"
    )
    model, classes, meta = load_classifier(args.checkpoint, device)
    transform = build_transforms(train=False)
    category = (meta.get("category") or {})

    results = []
    for image_path in iter_images(args.path):
        row = predict_image(model, classes, image_path, device, transform)
        row["category"] = category.get(row["label"], "unknown")
        row["uncertain"] = row["confidence"] < args.min_confidence
        results.append(row)
        flag = " [?]" if row["uncertain"] else ""
        print(
            f"{row['label']:8s} {row['confidence']*100:5.1f}%  "
            f"{row['category']:10s}  {image_path.name}{flag}"
        )

    out = MODELS_DIR / "garment4_infer_last.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
