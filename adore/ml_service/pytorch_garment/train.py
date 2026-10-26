"""Train the 4-class garment classifier (CPU-friendly ResNet18 by default)."""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from tqdm import tqdm

from .config import (
    CLASS_ORDER,
    CONFUSION_NAME,
    DEFAULT_DATASET,
    LABELS_NAME,
    METRICS_NAME,
    MODEL_NAME,
    MODELS_DIR,
)
from .dataset import GarmentDataset, load_split_rows
from .model import build_model, set_backbone_trainable


def class_weights_from_counts(counts: list[int], device: torch.device) -> torch.Tensor:
    total = float(sum(counts))
    weights = []
    for c in counts:
        weights.append(total / (len(counts) * max(c, 1)))
    tensor = torch.tensor(weights, dtype=torch.float32, device=device)
    return tensor / tensor.mean()


@torch.no_grad()
def evaluate(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> dict:
    model.eval()
    total_loss = 0.0
    n = 0
    conf = np.zeros((len(CLASS_ORDER), len(CLASS_ORDER)), dtype=np.int64)
    for images, targets, _paths in loader:
        images = images.to(device)
        targets = targets.to(device)
        logits = model(images)
        loss = criterion(logits, targets)
        total_loss += float(loss.item()) * images.size(0)
        n += images.size(0)
        preds = logits.argmax(dim=1)
        for t, p in zip(targets.cpu().tolist(), preds.cpu().tolist()):
            conf[t, p] += 1

    per_class = {}
    f1s = []
    for i, name in enumerate(CLASS_ORDER):
        tp = int(conf[i, i])
        fp = int(conf[:, i].sum() - tp)
        fn = int(conf[i, :].sum() - tp)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall)
            else 0.0
        )
        per_class[name] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": int(conf[i, :].sum()),
        }
        f1s.append(f1)
    acc = float(np.trace(conf) / max(conf.sum(), 1))
    return {
        "loss": total_loss / max(n, 1),
        "accuracy": acc,
        "macro_f1": float(np.mean(f1s)) if f1s else 0.0,
        "per_class": per_class,
        "confusion": conf.tolist(),
    }


def plot_confusion(conf: list[list[int]], path: Path) -> None:
    matrix = np.asarray(conf, dtype=np.float64)
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(matrix, interpolation="nearest", cmap="Blues")
    ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    ax.set(
        xticks=range(len(CLASS_ORDER)),
        yticks=range(len(CLASS_ORDER)),
        xticklabels=CLASS_ORDER,
        yticklabels=CLASS_ORDER,
        ylabel="True",
        xlabel="Predicted",
        title="Garment 4-class confusion",
    )
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    thresh = matrix.max() / 2.0 if matrix.size else 0
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            ax.text(
                j,
                i,
                int(matrix[i, j]),
                ha="center",
                va="center",
                color="white" if matrix[i, j] > thresh else "black",
                fontsize=9,
            )
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def train(args: argparse.Namespace) -> dict:
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    print(f"Device: {device}")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    train_rows = load_split_rows(args.dataset, "train")
    val_rows = load_split_rows(args.dataset, "val")
    test_rows = load_split_rows(args.dataset, "test")
    if not train_rows:
        raise SystemExit(f"No training images under {args.dataset}")

    train_ds = GarmentDataset(
        train_rows, train=True, max_per_class=args.max_per_class, seed=args.seed
    )
    val_ds = GarmentDataset(
        val_rows, train=False, max_per_class=args.max_per_class, seed=args.seed
    )
    test_ds = GarmentDataset(
        test_rows, train=False, max_per_class=None, seed=args.seed
    )

    train_counts = [0] * len(CLASS_ORDER)
    for _, y in train_ds.samples:
        train_counts[y] += 1
    print("Train counts:", dict(zip(CLASS_ORDER, train_counts)))

    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.workers,
        pin_memory=device.type == "cuda",
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.workers,
        pin_memory=device.type == "cuda",
    )
    test_loader = DataLoader(
        test_ds,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.workers,
        pin_memory=device.type == "cuda",
    )

    model = build_model(
        args.backbone,
        num_classes=len(CLASS_ORDER),
        pretrained=not args.no_pretrained,
        freeze_backbone=args.freeze_backbone,
    ).to(device)

    weights = class_weights_from_counts(train_counts, device)
    criterion = nn.CrossEntropyLoss(weight=weights)
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(params, lr=args.lr, weight_decay=args.weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="max", factor=0.5, patience=2
    )

    history = []
    best_f1 = -1.0
    best_path = MODELS_DIR / args.out_name
    epochs_no_improve = 0
    stage2_done = False

    for epoch in range(1, args.epochs + 1):
        # Staged fine-tuning: unfreeze backbone after warmup epochs.
        if (
            args.freeze_backbone
            and not stage2_done
            and epoch == args.unfreeze_epoch
        ):
            set_backbone_trainable(model, True)
            optimizer = torch.optim.AdamW(
                model.parameters(), lr=args.lr * 0.2, weight_decay=args.weight_decay
            )
            scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
                optimizer, mode="max", factor=0.5, patience=2
            )
            stage2_done = True
            print(f"Epoch {epoch}: unfroze backbone, lr={args.lr * 0.2}")

        model.train()
        running = 0.0
        seen = 0
        correct = 0
        t0 = time.time()
        for images, targets, _paths in tqdm(train_loader, desc=f"train {epoch}"):
            images = images.to(device)
            targets = targets.to(device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(images)
            loss = criterion(logits, targets)
            loss.backward()
            optimizer.step()
            running += float(loss.item()) * images.size(0)
            seen += images.size(0)
            correct += int((logits.argmax(1) == targets).sum().item())

        train_loss = running / max(seen, 1)
        train_acc = correct / max(seen, 1)
        val_metrics = evaluate(model, val_loader, criterion, device)
        scheduler.step(val_metrics["macro_f1"])

        row = {
            "epoch": epoch,
            "train_loss": round(train_loss, 4),
            "train_acc": round(train_acc, 4),
            "val_loss": round(val_metrics["loss"], 4),
            "val_acc": round(val_metrics["accuracy"], 4),
            "val_macro_f1": round(val_metrics["macro_f1"], 4),
            "per_class": val_metrics["per_class"],
            "seconds": round(time.time() - t0, 1),
        }
        history.append(row)
        print(
            f"Epoch {epoch}: train_acc={train_acc:.3f} "
            f"val_acc={val_metrics['accuracy']:.3f} "
            f"val_macro_f1={val_metrics['macro_f1']:.3f}"
        )
        for name, stats in val_metrics["per_class"].items():
            print(
                f"  {name:8s} P={stats['precision']:.3f} "
                f"R={stats['recall']:.3f} F1={stats['f1']:.3f} "
                f"n={stats['support']}"
            )

        if val_metrics["macro_f1"] > best_f1 + 1e-4:
            best_f1 = val_metrics["macro_f1"]
            epochs_no_improve = 0
            torch.save(
                {
                    "model_state": model.state_dict(),
                    "backbone": args.backbone,
                    "classes": list(CLASS_ORDER),
                    "val_macro_f1": best_f1,
                    "epoch": epoch,
                },
                best_path,
            )
            plot_confusion(val_metrics["confusion"], MODELS_DIR / CONFUSION_NAME)
            print(f"  saved {best_path}")
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= args.patience:
                print(f"Early stopping at epoch {epoch}")
                break

    # Load best and evaluate on test.
    ckpt = torch.load(best_path, map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model_state"])
    test_metrics = evaluate(model, test_loader, criterion, device)
    plot_confusion(test_metrics["confusion"], MODELS_DIR / CONFUSION_NAME)

    labels_payload = {
        "classes": list(CLASS_ORDER),
        "displayName": {
            "shirt": "Shirt",
            "t-shirt": "T-shirt",
            "jacket": "Jacket",
            "pants": "Pants/Trousers",
        },
        "backbone": args.backbone,
        "imageSize": 224,
        "category": {
            "shirt": "upperwear",
            "t-shirt": "upperwear",
            "jacket": "upperwear",
            "pants": "lowerwear",
        },
    }
    (MODELS_DIR / LABELS_NAME).write_text(
        json.dumps(labels_payload, indent=2), encoding="utf-8"
    )
    metrics_payload = {
        "history": history,
        "best_val_macro_f1": best_f1,
        "test": {
            "accuracy": test_metrics["accuracy"],
            "macro_f1": test_metrics["macro_f1"],
            "per_class": test_metrics["per_class"],
            "confusion": test_metrics["confusion"],
        },
        "train_counts": dict(zip(CLASS_ORDER, train_counts)),
        "class_weights": weights.detach().cpu().tolist(),
        "device": str(device),
        "backbone": args.backbone,
    }
    (MODELS_DIR / METRICS_NAME).write_text(
        json.dumps(metrics_payload, indent=2), encoding="utf-8"
    )
    print("Test accuracy:", round(test_metrics["accuracy"], 4))
    print("Test macro-F1:", round(test_metrics["macro_f1"], 4))
    print(f"Wrote {MODELS_DIR / LABELS_NAME}")
    print(f"Wrote {MODELS_DIR / METRICS_NAME}")
    return metrics_payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument(
        "--backbone",
        default="resnet18",
        choices=["resnet18", "resnet50", "efficientnet_b0"],
    )
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--patience", type=int, default=4)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-per-class", type=int, default=None)
    parser.add_argument("--freeze-backbone", action="store_true")
    parser.add_argument("--unfreeze-epoch", type=int, default=3)
    parser.add_argument("--no-pretrained", action="store_true")
    parser.add_argument("--cpu", action="store_true")
    parser.add_argument("--out-name", default=MODEL_NAME)
    args = parser.parse_args()
    train(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
