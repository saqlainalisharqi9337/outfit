"""Train dress vs upperwear gate (stops tops becoming one-piece dress).

Classes: dress | upperwear (shirt+t-shirt+jacket pooled)
Uses existing Adore dataset + any open_ prefixed images already imported.
Does not modify lowerwear training.
"""

from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

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
CLASS_ORDER = ("dress", "upperwear")
SOURCE = (
    ("one-piece", "dress", "dress"),
    ("upperwear", "shirt", "upperwear"),
    ("upperwear", "tshirt", "upperwear"),
    ("upperwear", "t-shirt", "upperwear"),
    ("upperwear", "jacket", "upperwear"),
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
                transforms.RandomResizedCrop(IMAGE_SIZE, scale=(0.8, 1.0)),
                transforms.RandomHorizontalFlip(),
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


class GateDataset(Dataset):
    def __init__(self, rows, *, train: bool, max_per_class: int | None, seed: int = 42):
        idx = {n: i for i, n in enumerate(CLASS_ORDER)}
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
            self.samples.extend((p, idx[lab]) for p in paths)
        rng.shuffle(self.samples)
        self.tf = transforms_for(train)

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, i):
        path, y = self.samples[i]
        with Image.open(path) as im:
            x = self.tf(im.convert("RGB"))
        return x, y


@torch.no_grad()
def evaluate(model, loader, criterion, device):
    model.eval()
    conf = np.zeros((2, 2), dtype=np.int64)
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
        "accuracy": float(np.trace(conf) / max(conf.sum(), 1)),
        "macro_f1": float(np.mean(f1s)),
        "per_class": per,
        "confusion": conf.tolist(),
        "loss": loss_sum / max(n, 1),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    ap.add_argument("--epochs", type=int, default=5)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--max-per-class", type=int, default=800)
    ap.add_argument("--cpu", action="store_true")
    args = ap.parse_args()

    device = torch.device("cpu" if args.cpu or not torch.cuda.is_available() else "cuda")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    train_ds = GateDataset(
        collect(args.dataset, "train"), train=True, max_per_class=args.max_per_class
    )
    val_ds = GateDataset(
        collect(args.dataset, "val"), train=False, max_per_class=args.max_per_class
    )
    test_ds = GateDataset(
        collect(args.dataset, "test"), train=False, max_per_class=None
    )
    print("train", len(train_ds), "val", len(val_ds), "test", len(test_ds))

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False)
    test_loader = DataLoader(test_ds, batch_size=args.batch_size, shuffle=False)

    model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
    model.fc = nn.Linear(model.fc.in_features, 2)
    model = model.to(device)
    criterion = nn.CrossEntropyLoss()
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr)

    best_f1, out = -1.0, MODELS_DIR / "dress_upperwear_gate.pt"
    history = []
    for epoch in range(1, args.epochs + 1):
        model.train()
        correct, n = 0, 0
        t0 = time.time()
        for x, y in tqdm(train_loader, desc=f"gate {epoch}"):
            x, y = x.to(device), y.to(device)
            opt.zero_grad(set_to_none=True)
            logits = model(x)
            loss = criterion(logits, y)
            loss.backward()
            opt.step()
            correct += int((logits.argmax(1) == y).sum().item())
            n += x.size(0)
        val = evaluate(model, val_loader, criterion, device)
        history.append(
            {
                "epoch": epoch,
                "train_acc": round(correct / max(n, 1), 4),
                "val": val,
                "seconds": round(time.time() - t0, 1),
            }
        )
        print(
            f"Epoch {epoch}: val_acc={val['accuracy']:.3f} "
            f"macro_f1={val['macro_f1']:.3f}"
        )
        for name, s in val["per_class"].items():
            print(f"  {name:10s} F1={s['f1']:.3f} P={s['precision']:.3f} R={s['recall']:.3f}")
        if val["macro_f1"] > best_f1:
            best_f1 = val["macro_f1"]
            torch.save(
                {
                    "model_state": model.state_dict(),
                    "classes": list(CLASS_ORDER),
                    "backbone": "resnet18",
                },
                out,
            )
            print(f"  saved {out}")

    ckpt = torch.load(out, map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model_state"])
    test = evaluate(model, test_loader, criterion, device)
    (MODELS_DIR / "dress_upperwear_gate_labels.json").write_text(
        json.dumps({"classes": list(CLASS_ORDER), "backbone": "resnet18"}, indent=2),
        encoding="utf-8",
    )
    (MODELS_DIR / "dress_upperwear_gate_metrics.json").write_text(
        json.dumps({"history": history, "best_val_macro_f1": best_f1, "test": test}, indent=2),
        encoding="utf-8",
    )
    print("TEST", test["per_class"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
