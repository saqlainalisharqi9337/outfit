"""Train shoes / flats / sneakers / heels footwear specialist (PyTorch).

Sandals: no folder exists in D:\\fyp project\\dataset. Inference falls back
to ImageNet ``sandal`` → sandals. Do not touch lowerwear or dress models.

Outputs:
    models/footwear4_resnet18.pt
    models/footwear4_labels.json
    models/footwear4_metrics.json
    models/footwear4_confusion.png
"""

from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms
from tqdm import tqdm

DEFAULT_DATASET = Path(r"D:\fyp project\dataset")
MODELS_DIR = Path(__file__).resolve().parent / "models"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
CLASS_ORDER = ("shoes", "flats", "sneakers", "heels")
SOURCE = (
    ("footwear", "shoes", "shoes"),
    ("footwear", "flats", "flats"),
    ("footwear", "sneakers", "sneakers"),
    ("footwear", "heels", "heels"),
)
IMAGE_SIZE = 224


def collect(root: Path, split: str) -> list[tuple[Path, str]]:
    base = root / split / split
    rows: list[tuple[Path, str]] = []
    if not base.is_dir():
        return rows
    for family, leaf, label in SOURCE:
        folder = base / family / leaf
        if not folder.is_dir():
            continue
        for path in folder.rglob("*"):
            if path.is_file() and path.suffix.lower() in EXTS:
                rows.append((path, label))
    return rows


def transforms_for(train: bool):
    if train:
        return transforms.Compose(
            [
                transforms.Resize((IMAGE_SIZE + 24, IMAGE_SIZE + 24)),
                transforms.RandomResizedCrop(IMAGE_SIZE, scale=(0.80, 1.0), ratio=(0.9, 1.2)),
                transforms.RandomHorizontalFlip(),
                transforms.RandomRotation(10),
                transforms.ColorJitter(0.15, 0.15, 0.1, 0.02),
                transforms.ToTensor(),
                transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225)),
            ]
        )
    return transforms.Compose(
        [
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225)),
        ]
    )


class FootwearDataset(Dataset):
    def __init__(self, rows, *, train: bool, max_per_class: int | None, seed: int = 42):
        self.idx = {n: i for i, n in enumerate(CLASS_ORDER)}
        grouped = {n: [] for n in CLASS_ORDER}
        for p, lab in rows:
            if lab in grouped:
                grouped[lab].append(p)
        rng = random.Random(seed)
        self.samples: list[tuple[Path, int]] = []
        for lab in CLASS_ORDER:
            paths = list(grouped[lab])
            rng.shuffle(paths)
            if max_per_class:
                paths = paths[:max_per_class]
            self.samples.extend((p, self.idx[lab]) for p in paths)
        rng.shuffle(self.samples)
        self.tf = transforms_for(train)

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, i):
        path, y = self.samples[i]
        with Image.open(path) as im:
            x = self.tf(im.convert("RGB"))
        return x, y


def build_model(num_classes: int, freeze: bool) -> nn.Module:
    model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
    model.fc = nn.Linear(model.fc.in_features, num_classes)
    if freeze:
        for name, p in model.named_parameters():
            if not name.startswith("fc."):
                p.requires_grad = False
    return model


@torch.no_grad()
def evaluate(model, loader, criterion, device):
    model.eval()
    conf = np.zeros((len(CLASS_ORDER), len(CLASS_ORDER)), dtype=np.int64)
    loss_sum, n = 0.0, 0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        logits = model(x)
        loss_sum += float(criterion(logits, y).item()) * x.size(0)
        n += x.size(0)
        for t, p in zip(y.cpu().tolist(), logits.argmax(1).cpu().tolist()):
            conf[t, p] += 1
    per = {}
    f1s = []
    for i, name in enumerate(CLASS_ORDER):
        tp = int(conf[i, i])
        fp = int(conf[:, i].sum() - tp)
        fn = int(conf[i, :].sum() - tp)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        per[name] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "support": int(conf[i].sum()),
        }
        f1s.append(f1)
    return {
        "loss": loss_sum / max(n, 1),
        "accuracy": float(np.trace(conf) / max(conf.sum(), 1)),
        "macro_f1": float(np.mean(f1s)),
        "per_class": per,
        "confusion": conf.tolist(),
    }


def plot_confusion(conf, path: Path):
    m = np.asarray(conf, dtype=float)
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(m, cmap="Blues")
    fig.colorbar(im, ax=ax, fraction=0.046)
    ax.set_xticks(range(len(CLASS_ORDER)), CLASS_ORDER, rotation=30, ha="right")
    ax.set_yticks(range(len(CLASS_ORDER)), CLASS_ORDER)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title("Footwear (shoes/flats/sneakers/heels)")
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            ax.text(j, i, int(m[i, j]), ha="center", va="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    ap.add_argument("--epochs", type=int, default=6)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--max-per-class", type=int, default=500)
    ap.add_argument("--patience", type=int, default=3)
    ap.add_argument("--freeze-backbone", action="store_true")
    ap.add_argument("--unfreeze-epoch", type=int, default=2)
    ap.add_argument("--cpu", action="store_true")
    args = ap.parse_args()

    device = torch.device("cpu" if args.cpu or not torch.cuda.is_available() else "cuda")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    n_cls = len(CLASS_ORDER)
    train_ds = FootwearDataset(
        collect(args.dataset, "train"), train=True, max_per_class=args.max_per_class
    )
    val_ds = FootwearDataset(
        collect(args.dataset, "val"), train=False, max_per_class=args.max_per_class
    )
    test_ds = FootwearDataset(
        collect(args.dataset, "test"), train=False, max_per_class=None
    )
    counts = [0] * n_cls
    for _, y in train_ds.samples:
        counts[y] += 1
    print("Train counts:", dict(zip(CLASS_ORDER, counts)))
    print("NOTE: footwear/sandals folder is missing — sandals use ImageNet at inference.")

    train_loader = DataLoader(
        train_ds, batch_size=args.batch_size, shuffle=True, num_workers=0
    )
    val_loader = DataLoader(
        val_ds, batch_size=args.batch_size, shuffle=False, num_workers=0
    )
    test_loader = DataLoader(
        test_ds, batch_size=args.batch_size, shuffle=False, num_workers=0
    )

    model = build_model(n_cls, args.freeze_backbone).to(device)
    w = torch.tensor(
        [sum(counts) / (n_cls * max(c, 1)) for c in counts],
        dtype=torch.float32,
        device=device,
    )
    w = w / w.mean()
    criterion = nn.CrossEntropyLoss(weight=w)
    opt = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad], lr=args.lr
    )
    sched = torch.optim.lr_scheduler.ReduceLROnPlateau(
        opt, mode="max", factor=0.5, patience=2
    )

    best_f1, bad, out = -1.0, 0, MODELS_DIR / "footwear4_resnet18.pt"
    history = []
    for epoch in range(1, args.epochs + 1):
        if args.freeze_backbone and epoch == args.unfreeze_epoch:
            for p in model.parameters():
                p.requires_grad = True
            opt = torch.optim.AdamW(model.parameters(), lr=args.lr * 0.2)
            sched = torch.optim.lr_scheduler.ReduceLROnPlateau(
                opt, mode="max", factor=0.5, patience=2
            )
            print(f"Epoch {epoch}: unfroze backbone")
        model.train()
        loss_sum, n, correct = 0.0, 0, 0
        t0 = time.time()
        for x, y in tqdm(train_loader, desc=f"footwear4 {epoch}"):
            x, y = x.to(device), y.to(device)
            opt.zero_grad(set_to_none=True)
            logits = model(x)
            loss = criterion(logits, y)
            loss.backward()
            opt.step()
            loss_sum += float(loss.item()) * x.size(0)
            n += x.size(0)
            correct += int((logits.argmax(1) == y).sum().item())
        val = evaluate(model, val_loader, criterion, device)
        sched.step(val["macro_f1"])
        row = {
            "epoch": epoch,
            "train_acc": round(correct / max(n, 1), 4),
            "val_acc": round(val["accuracy"], 4),
            "val_macro_f1": round(val["macro_f1"], 4),
            "per_class": val["per_class"],
            "seconds": round(time.time() - t0, 1),
        }
        history.append(row)
        print(
            f"Epoch {epoch}: val_acc={val['accuracy']:.3f} "
            f"macro_f1={val['macro_f1']:.3f}"
        )
        for name, s in val["per_class"].items():
            print(
                f"  {name:9s} F1={s['f1']:.3f} "
                f"P={s['precision']:.3f} R={s['recall']:.3f}"
            )
        if val["macro_f1"] > best_f1 + 1e-4:
            best_f1, bad = val["macro_f1"], 0
            torch.save(
                {
                    "model_state": model.state_dict(),
                    "classes": list(CLASS_ORDER),
                    "backbone": "resnet18",
                },
                out,
            )
            plot_confusion(val["confusion"], MODELS_DIR / "footwear4_confusion.png")
            print(f"  saved {out}")
        else:
            bad += 1
            if bad >= args.patience:
                print("Early stopping")
                break

    ckpt = torch.load(out, map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model_state"])
    test = evaluate(model, test_loader, criterion, device)
    plot_confusion(test["confusion"], MODELS_DIR / "footwear4_confusion.png")
    labels = {
        "classes": list(CLASS_ORDER),
        "sandals": "imagenet_only_no_folder",
        "category": {c: "footwear" for c in CLASS_ORDER} | {"sandals": "footwear"},
        "backbone": "resnet18",
        "imageSize": IMAGE_SIZE,
    }
    (MODELS_DIR / "footwear4_labels.json").write_text(
        json.dumps(labels, indent=2), encoding="utf-8"
    )
    (MODELS_DIR / "footwear4_metrics.json").write_text(
        json.dumps(
            {"history": history, "best_val_macro_f1": best_f1, "test": test}, indent=2
        ),
        encoding="utf-8",
    )
    print("Test accuracy", round(test["accuracy"], 4), "macro_f1", round(test["macro_f1"], 4))
    for name, s in test["per_class"].items():
        print(f"  {name:9s} F1={s['f1']:.3f} P={s['precision']:.3f} R={s['recall']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
