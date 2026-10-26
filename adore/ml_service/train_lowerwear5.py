"""Train 5-class lowerwear specialist.

trousers | shorts | skirt | shalwar | leggings

Uses datasets/lowerwear5 from prepare_lowerwear5_dataset.py.
Saves models/lowerwear5_resnet18.pt without overwriting trousers_gate
or trousers_shorts_skirt keras checkpoints.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms
from tqdm import tqdm

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "datasets" / "lowerwear5"
MODELS_DIR = ROOT / "models"
CANDIDATE_CLASSES = ("trousers", "shorts", "skirt", "shalwar", "leggings")
IMAGE_SIZE = 224
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
CLASSES: tuple[str, ...] = CANDIDATE_CLASSES


def discover_classes() -> tuple[str, ...]:
    found = []
    for name in CANDIDATE_CLASSES:
        folder = DATA / "train" / name
        n = 0
        if folder.is_dir():
            n = sum(1 for p in folder.iterdir() if p.is_file() and p.suffix.lower() in EXTS)
        if n >= 40:
            found.append(name)
    if not found:
        raise SystemExit("No lowerwear5 classes. Run prepare_lowerwear5_dataset.py.")
    return tuple(found)


def list_split(split: str) -> list[tuple[Path, int]]:
    rows: list[tuple[Path, int]] = []
    for i, name in enumerate(CLASSES):
        folder = DATA / split / name
        if not folder.is_dir():
            continue
        for path in folder.iterdir():
            if path.is_file() and path.suffix.lower() in EXTS:
                rows.append((path, i))
    return rows


def transforms_for(train: bool):
    if train:
        return transforms.Compose(
            [
                transforms.Resize((IMAGE_SIZE + 48, IMAGE_SIZE + 48)),
                transforms.RandomResizedCrop(
                    IMAGE_SIZE, scale=(0.55, 1.0), ratio=(0.7, 1.35)
                ),
                transforms.RandomHorizontalFlip(),
                transforms.RandomApply(
                    [transforms.RandomRotation(18)],
                    p=0.45,
                ),
                transforms.ColorJitter(0.28, 0.28, 0.18, 0.04),
                transforms.RandomAffine(degrees=0, translate=(0.08, 0.12)),
                transforms.ToTensor(),
                transforms.RandomApply(
                    [transforms.GaussianBlur(5, sigma=(0.1, 2.4))],
                    p=0.35,
                ),
                transforms.RandomErasing(p=0.28, scale=(0.02, 0.18), value="random"),
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


class FolderSet(Dataset):
    def __init__(self, rows: list[tuple[Path, int]], *, train: bool):
        self.rows = rows
        self.tf = transforms_for(train)

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        path, y = self.rows[i]
        with Image.open(path) as im:
            return self.tf(im.convert("RGB")), y


def build_model() -> nn.Module:
    model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
    model.fc = nn.Linear(model.fc.in_features, len(CLASSES))
    for name, param in model.named_parameters():
        param.requires_grad = (
            name.startswith("layer3")
            or name.startswith("layer4")
            or name.startswith("fc")
        )
    return model


@torch.no_grad()
def evaluate(model, loader, criterion, device):
    model.eval()
    conf = np.zeros((len(CLASSES), len(CLASSES)), dtype=np.int64)
    loss_sum, n = 0.0, 0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        logits = model(x)
        loss_sum += float(criterion(logits, y).item()) * x.size(0)
        n += x.size(0)
        pred = logits.argmax(1).cpu().numpy()
        for t, p in zip(y.cpu().numpy(), pred):
            conf[t, p] += 1
    support = conf.sum(axis=1).clip(min=1)
    recall = np.diag(conf) / support
    prec_den = conf.sum(axis=0).clip(min=1)
    precision = np.diag(conf) / prec_den
    f1 = np.where(
        (precision + recall) == 0,
        0,
        2 * precision * recall / (precision + recall),
    )
    acc = float(np.diag(conf).sum() / max(1, conf.sum()))
    per_class = {
        CLASSES[i]: {
            "precision": round(float(precision[i]), 4),
            "recall": round(float(recall[i]), 4),
            "f1": round(float(f1[i]), 4),
            "support": int(conf[i].sum()),
        }
        for i in range(len(CLASSES))
    }
    return {
        "loss": loss_sum / max(1, n),
        "accuracy": acc,
        "macro_f1": float(f1.mean()),
        "per_class": per_class,
        "confusion": conf.tolist(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--lr", type=float, default=2.5e-4)
    args = parser.parse_args()
    if not (DATA / "train").is_dir():
        raise SystemExit("Run prepare_lowerwear5_dataset.py first.")
    global CLASSES
    CLASSES = discover_classes()
    print("classes", CLASSES)

    device = torch.device("cpu")
    train_rows, val_rows, test_rows = (
        list_split("train"),
        list_split("val"),
        list_split("test"),
    )
    print("train", len(train_rows), "val", len(val_rows), "test", len(test_rows))
    counts = np.zeros(len(CLASSES), dtype=np.float64)
    for _, y in train_rows:
        counts[y] += 1
    weights = torch.tensor(1.0 / np.sqrt(np.maximum(counts, 1.0)), dtype=torch.float32)
    weights = weights / weights.mean()
    print("class weights", {CLASSES[i]: round(float(weights[i]), 3) for i in range(len(CLASSES))})
    train_loader = DataLoader(
        FolderSet(train_rows, train=True),
        batch_size=args.batch,
        shuffle=True,
        num_workers=0,
        drop_last=True,
    )
    val_loader = DataLoader(
        FolderSet(val_rows, train=False),
        batch_size=args.batch,
        shuffle=False,
        num_workers=0,
    )
    test_loader = DataLoader(
        FolderSet(test_rows, train=False),
        batch_size=args.batch,
        shuffle=False,
        num_workers=0,
    )
    model = build_model().to(device)
    criterion = nn.CrossEntropyLoss(weight=weights)
    optim = torch.optim.AdamW(
        (p for p in model.parameters() if p.requires_grad),
        lr=args.lr,
        weight_decay=1e-4,
    )
    best_f1 = -1.0
    best_state = None
    history = []
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    for epoch in range(1, args.epochs + 1):
        model.train()
        correct, seen, t0 = 0, 0, time.time()
        for x, y in tqdm(train_loader, desc=f"epoch {epoch}"):
            x, y = x.to(device), y.to(device)
            optim.zero_grad(set_to_none=True)
            logits = model(x)
            loss = criterion(logits, y)
            loss.backward()
            optim.step()
            correct += int((logits.argmax(1) == y).sum().item())
            seen += x.size(0)
        val = evaluate(model, val_loader, criterion, device)
        row = {
            "epoch": epoch,
            "train_acc": round(correct / max(1, seen), 4),
            "val_acc": round(val["accuracy"], 4),
            "val_macro_f1": round(val["macro_f1"], 4),
            "per_class": val["per_class"],
            "seconds": round(time.time() - t0, 1),
        }
        history.append(row)
        print(row)
        if val["macro_f1"] > best_f1:
            best_f1 = val["macro_f1"]
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    if best_state:
        model.load_state_dict(best_state)
    test = evaluate(model, test_loader, criterion, device)
    ckpt = {
        "classes": list(CLASSES),
        "model_state": model.state_dict(),
        "imageSize": IMAGE_SIZE,
        "backbone": "resnet18",
    }
    torch.save(ckpt, MODELS_DIR / "lowerwear5_resnet18.pt")
    category = {name: "lowerwear" for name in CLASSES}
    (MODELS_DIR / "lowerwear5_labels.json").write_text(
        json.dumps(
            {
                "classes": list(CLASSES),
                "category": category,
                "backbone": "resnet18",
                "imageSize": IMAGE_SIZE,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (MODELS_DIR / "lowerwear5_metrics.json").write_text(
        json.dumps(
            {"history": history, "best_val_macro_f1": best_f1, "test": test},
            indent=2,
        ),
        encoding="utf-8",
    )
    print("Test accuracy", round(test["accuracy"], 4), "macro_f1", round(test["macro_f1"], 4))
    print("saved", MODELS_DIR / "lowerwear5_resnet18.pt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
