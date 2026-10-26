"""Dump top misclassified images for each true→pred class pair."""

from __future__ import annotations

import argparse
import json
import shutil
from collections import defaultdict
from pathlib import Path

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
from tqdm import tqdm

from .config import (
    CLASS_ORDER,
    DEFAULT_DATASET,
    ERRORS_DIR_NAME,
    LABELS_NAME,
    MODEL_NAME,
    MODELS_DIR,
)
from .dataset import GarmentDataset, load_split_rows
from .model import build_model


@torch.no_grad()
def collect_errors(
    *,
    dataset_root: Path,
    split: str,
    ckpt_path: Path,
    out_dir: Path,
    top_k: int,
    batch_size: int,
    device: torch.device,
) -> dict:
    ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
    backbone = ckpt.get("backbone", "resnet18")
    classes = ckpt.get("classes", list(CLASS_ORDER))
    model = build_model(backbone, num_classes=len(classes), pretrained=False)
    model.load_state_dict(ckpt["model_state"])
    model.to(device)
    model.eval()

    rows = load_split_rows(dataset_root, split)
    ds = GarmentDataset(rows, train=False)
    loader = DataLoader(ds, batch_size=batch_size, shuffle=False, num_workers=0)

    buckets: dict[tuple[str, str], list[tuple[float, str, list[float]]]] = defaultdict(
        list
    )
    for images, targets, paths in tqdm(loader, desc=f"errors:{split}"):
        images = images.to(device)
        logits = model(images)
        probs = F.softmax(logits, dim=1)
        preds = probs.argmax(dim=1)
        for i in range(images.size(0)):
            true_i = int(targets[i])
            pred_i = int(preds[i])
            if true_i == pred_i:
                continue
            true_name = classes[true_i]
            pred_name = classes[pred_i]
            conf = float(probs[i, pred_i])
            score_row = probs[i].detach().cpu().tolist()
            buckets[(true_name, pred_name)].append((conf, paths[i], score_row))

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {"split": split, "pairs": {}}
    for (true_name, pred_name), items in sorted(buckets.items()):
        items.sort(key=lambda row: -row[0])
        keep = items[:top_k]
        pair_dir = out_dir / f"{true_name}__as__{pred_name}"
        pair_dir.mkdir(parents=True, exist_ok=True)
        saved = []
        for rank, (conf, src, scores) in enumerate(keep, start=1):
            src_path = Path(src)
            dest = pair_dir / f"{rank:02d}_conf{conf:.3f}_{src_path.name}"
            try:
                shutil.copy2(src_path, dest)
            except OSError:
                continue
            saved.append(
                {
                    "file": dest.name,
                    "source": str(src_path),
                    "confidence": round(conf, 4),
                    "scores": {
                        classes[i]: round(float(s), 4) for i, s in enumerate(scores)
                    },
                }
            )
        summary["pairs"][f"{true_name}->{pred_name}"] = {
            "count": len(items),
            "saved": saved,
        }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--split", default="val", choices=["train", "val", "test"])
    parser.add_argument("--checkpoint", type=Path, default=MODELS_DIR / MODEL_NAME)
    parser.add_argument("--out-dir", type=Path, default=MODELS_DIR / ERRORS_DIR_NAME)
    parser.add_argument("--top-k", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()

    if not args.checkpoint.is_file():
        raise SystemExit(f"Missing checkpoint: {args.checkpoint}. Train first.")

    device = torch.device(
        "cuda" if torch.cuda.is_available() and not args.cpu else "cpu"
    )
    summary = collect_errors(
        dataset_root=args.dataset,
        split=args.split,
        ckpt_path=args.checkpoint,
        out_dir=args.out_dir,
        top_k=args.top_k,
        batch_size=args.batch_size,
        device=device,
    )
    print(json.dumps({k: v["count"] for k, v in summary["pairs"].items()}, indent=2))
    print(f"Wrote samples under {args.out_dir}")
    labels = MODELS_DIR / LABELS_NAME
    if labels.is_file():
        print(f"Labels: {labels}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
