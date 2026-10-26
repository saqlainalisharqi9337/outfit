"""Mask R-CNN training: smoke test plus a capped small-run loop.

Not imported by FastAPI production. Full-dataset training requires --allow-full.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.utils.data import DataLoader

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parent
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from training.dataset import (
    BACKGROUND_ID,
    NUM_CLASSES,
    NUM_FOREGROUND,
    ClothingDetectionDataset,
    collate_fn,
    detection_paths,
)
from training.label_map import load_label_map
from training.preview_maskrcnn import write_previews

CHECKPOINT_DIR = REPO_ROOT / "checkpoints" / "maskrcnn"
LEGACY_CHECKPOINT_DIR = SERVICE_ROOT / "models" / "maskrcnn"
PREVIEW_DIR = REPO_ROOT / "evaluation_results" / "maskrcnn_pipeline_preview"
LOSS_KEYS = (
    "loss_classifier",
    "loss_box_reg",
    "loss_mask",
    "loss_objectness",
    "loss_rpn_box_reg",
)
SMOKE_MAX_IMAGES = 4
SMOKE_BATCH_SIZE = 1
SMOKE_NUM_WORKERS = 0
SMOKE_MIN_SIZE = 256
SMOKE_MAX_SIZE = 320
DEFAULT_SMALL_TRAIN = 100
DEFAULT_SMALL_VAL = 50
DEFAULT_SMALL_EPOCHS = 1


@dataclass
class TrainConfig:
    dataset_root: Path
    train_images: Path
    val_images: Path
    test_images: Path
    train_ann: Path
    val_ann: Path
    test_ann: Path
    num_classes: int
    batch_size: int
    learning_rate: float
    weight_decay: float
    num_epochs: int
    num_workers: int
    device: torch.device
    seed: int
    checkpoint_dir: Path
    momentum: float = 0.9
    min_size: int = 800
    max_size: int = 1333
    smoke_max_images: int = SMOKE_MAX_IMAGES
    max_train_images: int | None = DEFAULT_SMALL_TRAIN
    max_val_images: int | None = DEFAULT_SMALL_VAL
    pretrained: bool = True
    cpu_fast: bool = True
    print_every: int = 10
    subset_mode: str = "first"
    val_subset_mode: str | None = None
    score_threshold: float = 0.5
    train_image_ids: set[int] | None = None
    hflip_prob: float = 0.0


def select_device(requested: str = "auto") -> torch.device:
    name = (requested or "auto").strip().lower()
    if name == "cuda":
        if torch.cuda.is_available():
            return torch.device("cuda")
        print("CUDA requested but unavailable; using CPU")
        return torch.device("cpu")
    if name == "cpu":
        return torch.device("cpu")
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def default_config(*, smoke: bool, device: torch.device | None = None) -> TrainConfig:
    paths = detection_paths()
    device = device or select_device()
    cpu = device.type == "cpu"
    return TrainConfig(
        dataset_root=paths["root"],
        train_images=paths["train_images"],
        val_images=paths["val_images"],
        test_images=paths["test_images"],
        train_ann=paths["train_ann"],
        val_ann=paths["val_ann"],
        test_ann=paths["test_ann"],
        num_classes=NUM_CLASSES,
        batch_size=SMOKE_BATCH_SIZE if smoke or cpu else 2,
        learning_rate=0.005,
        weight_decay=0.0005,
        num_epochs=1 if smoke else DEFAULT_SMALL_EPOCHS,
        num_workers=SMOKE_NUM_WORKERS if smoke or cpu else 2,
        device=device,
        seed=42,
        checkpoint_dir=CHECKPOINT_DIR,
        min_size=SMOKE_MIN_SIZE if smoke or cpu else 800,
        max_size=SMOKE_MAX_SIZE if smoke or cpu else 1333,
        smoke_max_images=SMOKE_MAX_IMAGES,
        max_train_images=None if smoke else DEFAULT_SMALL_TRAIN,
        max_val_images=None if smoke else DEFAULT_SMALL_VAL,
        pretrained=True,
        cpu_fast=cpu,
    )


def apply_cpu_fast(model) -> None:
    model.rpn._pre_nms_top_n["training"] = 200
    model.rpn._pre_nms_top_n["testing"] = 100
    model.rpn._post_nms_top_n["training"] = 100
    model.rpn._post_nms_top_n["testing"] = 50
    model.roi_heads.detections_per_img = 20


def build_maskrcnn(
    num_classes: int = NUM_CLASSES,
    *,
    pretrained: bool,
    min_size: int,
    max_size: int,
    smoke_rpn: bool = False,
):
    from torchvision.models.detection import maskrcnn_resnet50_fpn
    from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
    from torchvision.models.detection.mask_rcnn import MaskRCNNPredictor

    kwargs: dict = {"min_size": min_size, "max_size": max_size}
    if pretrained:
        from torchvision.models.detection import MaskRCNN_ResNet50_FPN_Weights

        weights = getattr(MaskRCNN_ResNet50_FPN_Weights, "COCO_V1", None)
        if weights is None:
            weights = MaskRCNN_ResNet50_FPN_Weights.DEFAULT
        model = maskrcnn_resnet50_fpn(weights=weights, **kwargs)
    else:
        model = maskrcnn_resnet50_fpn(weights=None, weights_backbone=None, **kwargs)

    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
    in_features_mask = model.roi_heads.mask_predictor.conv5_mask.in_channels
    model.roi_heads.mask_predictor = MaskRCNNPredictor(in_features_mask, 256, num_classes)

    box_classes = int(model.roi_heads.box_predictor.cls_score.out_features)
    mask_classes = int(model.roi_heads.mask_predictor.mask_fcn_logits.out_channels)
    if box_classes != num_classes or mask_classes != num_classes:
        raise RuntimeError(
            f"head mismatch: box={box_classes} mask={mask_classes} expected {num_classes}"
        )
    if smoke_rpn:
        apply_cpu_fast(model)
    return model


def head_class_counts(model) -> tuple[int, int]:
    box_classes = int(model.roi_heads.box_predictor.cls_score.out_features)
    mask_classes = int(model.roi_heads.mask_predictor.mask_fcn_logits.out_channels)
    return box_classes, mask_classes


def _finite(value: torch.Tensor | float) -> bool:
    tensor = value if isinstance(value, torch.Tensor) else torch.tensor(float(value))
    return bool(torch.isfinite(tensor).all().item())


def _detach_loss_dict(loss_dict: dict[str, torch.Tensor]) -> dict[str, float]:
    out = {key: float(loss_dict[key].detach().cpu()) for key in LOSS_KEYS if key in loss_dict}
    out["total_loss"] = float(sum(loss_dict.values()).detach().cpu())
    return out


def _to_device(images, targets, device):
    images = [img.to(device) for img in images]
    targets = [{k: v.to(device) for k, v in t.items()} for t in targets]
    return images, targets


def make_optimizer(model, cfg: TrainConfig):
    return torch.optim.SGD(
        [p for p in model.parameters() if p.requires_grad],
        lr=cfg.learning_rate,
        momentum=cfg.momentum,
        weight_decay=cfg.weight_decay,
    )


def config_payload(cfg: TrainConfig, class_names: list[str]) -> dict[str, Any]:
    return {
        "num_classes": cfg.num_classes,
        "batch_size": cfg.batch_size,
        "learning_rate": cfg.learning_rate,
        "weight_decay": cfg.weight_decay,
        "num_epochs": cfg.num_epochs,
        "num_workers": cfg.num_workers,
        "device": str(cfg.device),
        "seed": cfg.seed,
        "min_size": cfg.min_size,
        "max_size": cfg.max_size,
        "max_train_images": cfg.max_train_images,
        "max_val_images": cfg.max_val_images,
        "pretrained": cfg.pretrained,
        "subset_mode": cfg.subset_mode,
        "score_threshold": cfg.score_threshold,
        "class_names": list(class_names),
        "background_id": BACKGROUND_ID,
        "num_foreground": NUM_FOREGROUND,
    }


def save_checkpoint(
    path: Path,
    model,
    optimizer,
    *,
    epoch: int,
    train_loss: float,
    val_loss: float | None,
    losses: dict[str, float],
    cfg: TrainConfig,
    class_names: list[str],
    best: bool = False,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "epoch": int(epoch),
        "train_loss": float(train_loss),
        "val_loss": None if val_loss is None else float(val_loss),
        "losses": dict(losses),
        "class_names": list(class_names),
        "num_classes": int(cfg.num_classes),
        "config": config_payload(cfg, class_names),
        "best": bool(best),
    }
    torch.save(payload, path)


def load_checkpoint(path: Path, model, optimizer=None, map_location: str | torch.device = "cpu"):
    try:
        ckpt = torch.load(path, map_location=map_location, weights_only=False)
    except TypeError:
        ckpt = torch.load(path, map_location=map_location)
    model.load_state_dict(ckpt["model_state_dict"])
    if optimizer is not None and ckpt.get("optimizer_state_dict") is not None:
        optimizer.load_state_dict(ckpt["optimizer_state_dict"])
    return ckpt


def instantiate_model(cfg: TrainConfig):
    try:
        model = build_maskrcnn(
            cfg.num_classes,
            pretrained=cfg.pretrained,
            min_size=cfg.min_size,
            max_size=cfg.max_size,
            smoke_rpn=cfg.cpu_fast,
        )
        source = "pretrained COCO weights" if cfg.pretrained else "random initialization"
    except Exception as exc:
        if not cfg.pretrained:
            raise
        print(f"Pretrained COCO weights unavailable ({type(exc).__name__}: {exc})")
        print("Continuing with randomly initialized weights")
        model = build_maskrcnn(
            cfg.num_classes,
            pretrained=False,
            min_size=cfg.min_size,
            max_size=cfg.max_size,
            smoke_rpn=cfg.cpu_fast,
        )
        source = "random initialization (pretrained fallback)"
    return model, source


def _accumulate_losses(bucket: dict[str, float], loss_dict: dict[str, torch.Tensor], count: int) -> int:
    detached = _detach_loss_dict(loss_dict)
    for key, value in detached.items():
        if not _finite(value):
            raise RuntimeError(f"{key} is not finite: {value}")
        bucket[key] = bucket.get(key, 0.0) + value
    return count + 1


def _mean_losses(bucket: dict[str, float], count: int) -> dict[str, float]:
    if count <= 0:
        return {key: float("nan") for key in (*LOSS_KEYS, "total_loss")}
    return {key: bucket[key] / count for key in bucket}


def run_one_epoch(
    model,
    loader: DataLoader,
    device: torch.device,
    *,
    optimizer=None,
    print_every: int = 10,
    split: str = "train",
) -> dict[str, float]:
    train = optimizer is not None
    model.train()
    bucket: dict[str, float] = {}
    count = 0
    skipped = 0
    total_steps = len(loader)
    for step, (images, targets) in enumerate(loader, start=1):
        try:
            images, targets = _to_device(images, targets, device)
            if train:
                optimizer.zero_grad(set_to_none=True)
                loss_dict = model(images, targets)
                total = sum(loss_dict.values())
                if not _finite(total):
                    raise RuntimeError(f"non-finite total loss {total}")
                total.backward()
                optimizer.step()
            else:
                with torch.no_grad():
                    loss_dict = model(images, targets)
            count = _accumulate_losses(bucket, loss_dict, count)
        except Exception as exc:
            skipped += 1
            print(f"  {split} step {step}: skipped ({type(exc).__name__}: {exc})")
            if train and optimizer is not None:
                optimizer.zero_grad(set_to_none=True)
            continue
        if print_every and step % print_every == 0:
            current = _mean_losses(bucket, count)
            print(
                f"  {split} step {step}/{total_steps}  "
                f"total={current.get('total_loss', float('nan')):.4f}  "
                f"cls={current.get('loss_classifier', float('nan')):.4f}  "
                f"box={current.get('loss_box_reg', float('nan')):.4f}  "
                f"mask={current.get('loss_mask', float('nan')):.4f}"
            )
    means = _mean_losses(bucket, count)
    means["steps"] = float(count)
    means["skipped"] = float(skipped)
    return means


def _label_histogram(dataset: ClothingDetectionDataset) -> dict[str, int]:
    counts = {name: 0 for name in dataset.label_names}
    for row in dataset.records:
        for ann in row["anns"]:
            cat_id = int(ann.get("category_id") or 0)
            if cat_id not in dataset.cat_id_to_label:
                continue
            label = dataset.cat_id_to_label[cat_id]
            counts[dataset.label_names[label - 1]] += 1
    return counts


def run_training(
    cfg: TrainConfig,
    *,
    resume: Path | None = None,
    init_from: Path | None = None,
) -> dict[str, Any]:
    if resume is not None and init_from is not None:
        raise ValueError("Use either --resume or --init-from, not both")
    label_map = load_label_map()
    print("Loading training subset...")
    train_ds = ClothingDetectionDataset(
        cfg.train_images,
        cfg.train_ann,
        label_map,
        max_images=cfg.max_train_images,
        skip_invalid=True,
        subset_mode=cfg.subset_mode,
        seed=cfg.seed,
        image_ids=cfg.train_image_ids,
        hflip_prob=cfg.hflip_prob,
    )
    val_mode = cfg.val_subset_mode or cfg.subset_mode
    print("Loading validation subset...")
    val_ds = ClothingDetectionDataset(
        cfg.val_images,
        cfg.val_ann,
        label_map,
        max_images=cfg.max_val_images,
        skip_invalid=True,
        subset_mode=val_mode,
        seed=cfg.seed,
    )
    print()
    print("Train images in COCO JSON:", train_ds.total_images_in_json)
    print("Train subset used:", len(train_ds))
    print("Val images in COCO JSON:", val_ds.total_images_in_json)
    print("Val subset used:", len(val_ds))
    print("Foreground classes:", NUM_FOREGROUND)
    print("Total classes:", NUM_CLASSES)
    print("Device:", cfg.device)
    print("Epochs:", cfg.num_epochs)
    print("Batch size:", cfg.batch_size)
    print("Learning rate:", cfg.learning_rate)
    print("Workers:", cfg.num_workers)
    print("Subset mode:", cfg.subset_mode)
    print("Train horizontal-flip probability:", cfg.hflip_prob)
    print("min_size / max_size:", cfg.min_size, "/", cfg.max_size)
    print("Eval score threshold (stored, not used while training):", cfg.score_threshold)
    print("Checkpoint directory:", cfg.checkpoint_dir)
    if resume is not None:
        print("Resume checkpoint:", resume)
    if init_from is not None:
        print("Init-from checkpoint (weights only, optimizer reset, epoch counter reset):", init_from)
    train_hist = _label_histogram(train_ds)
    val_hist = _label_histogram(val_ds)
    print("Train subset instance counts:")
    for name, count in train_hist.items():
        print(f"  {name}: {count}")
    print()
    print("Val subset instance counts:")
    for name, count in val_hist.items():
        print(f"  {name}: {count}")
    print()
    subset_stats = {
        "train_images": len(train_ds),
        "val_images": len(val_ds),
        "train_histogram": train_hist,
        "val_histogram": val_hist,
        "subset_mode": cfg.subset_mode,
        "seed": cfg.seed,
        "hflip_prob": cfg.hflip_prob,
        "train_id_list_size": None if cfg.train_image_ids is None else len(cfg.train_image_ids),
    }
    cfg.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    (cfg.checkpoint_dir / "subset_stats.json").write_text(
        json.dumps(subset_stats, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote subset stats: {cfg.checkpoint_dir / 'subset_stats.json'}")
    print()

    train_loader = DataLoader(
        train_ds,
        batch_size=cfg.batch_size,
        shuffle=True,
        num_workers=cfg.num_workers,
        collate_fn=collate_fn,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=cfg.batch_size,
        shuffle=False,
        num_workers=cfg.num_workers,
        collate_fn=collate_fn,
    )

    model, source = instantiate_model(cfg)
    model.to(cfg.device)
    optimizer = make_optimizer(model, cfg)
    start_epoch = 1
    best_val = float("inf")
    best_epoch = 0
    history: list[dict[str, Any]] = []
    if init_from is not None:
        if not Path(init_from).is_file():
            raise FileNotFoundError(f"Init-from checkpoint not found: {init_from}")
        ckpt = load_checkpoint(init_from, model, optimizer=None, map_location=cfg.device)
        source = f"weights from {init_from}"
        print(
            f"Loaded init-from weights ({init_from}); "
            f"source_epoch={ckpt.get('epoch')} source_best={ckpt.get('best')} "
            f"source_val_loss={ckpt.get('val_loss')}"
        )
        print("Optimizer re-initialized; training epochs restart at 1")
    elif resume is not None:
        if not Path(resume).is_file():
            raise FileNotFoundError(f"Resume checkpoint not found: {resume}")
        ckpt = load_checkpoint(resume, model, optimizer, map_location=cfg.device)
        start_epoch = int(ckpt.get("epoch") or 0) + 1
        if ckpt.get("val_loss") is not None:
            best_val = float(ckpt["val_loss"])
        best_epoch = int(ckpt.get("epoch") or 0)
        print(f"Resumed from {resume} at epoch {start_epoch}")
    box_classes, mask_classes = head_class_counts(model)
    print(f"Mask R-CNN initialized ({source})")
    print(f"box predictor classes: {box_classes}")
    print(f"mask predictor classes: {mask_classes}")
    print()

    cfg.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    LEGACY_CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    for epoch in range(start_epoch, cfg.num_epochs + 1):
        epoch_start = time.perf_counter()
        print(f"===== Epoch {epoch}/{cfg.num_epochs} =====")
        train_losses = run_one_epoch(
            model,
            train_loader,
            cfg.device,
            optimizer=optimizer,
            print_every=cfg.print_every,
            split="train",
        )
        val_losses = run_one_epoch(
            model,
            val_loader,
            cfg.device,
            optimizer=None,
            print_every=0,
            split="val",
        )
        elapsed = time.perf_counter() - epoch_start
        train_loss = float(train_losses.get("total_loss", float("nan")))
        val_loss = float(val_losses.get("total_loss", float("nan")))
        print()
        print(f"EPOCH {epoch} SUMMARY")
        print(f"  elapsed_seconds = {elapsed:.1f}")
        print(f"  train_loss = {train_loss:.6f}")
        print(f"  val_loss = {val_loss:.6f}")
        for key in LOSS_KEYS:
            print(f"  train_{key} = {train_losses.get(key, float('nan')):.6f}")
        for key in LOSS_KEYS:
            print(f"  val_{key} = {val_losses.get(key, float('nan')):.6f}")
        print()

        row = {
            "epoch": epoch,
            "elapsed_seconds": elapsed,
            "train": train_losses,
            "val": val_losses,
        }
        history.append(row)
        save_checkpoint(
            cfg.checkpoint_dir / "last_model.pth",
            model,
            optimizer,
            epoch=epoch,
            train_loss=train_loss,
            val_loss=val_loss,
            losses={"train": train_losses, "val": val_losses},
            cfg=cfg,
            class_names=train_ds.label_names,
            best=False,
        )
        improved = val_loss < best_val
        if improved:
            best_val = val_loss
            best_epoch = epoch
            save_checkpoint(
                cfg.checkpoint_dir / "best_model.pth",
                model,
                optimizer,
                epoch=epoch,
                train_loss=train_loss,
                val_loss=val_loss,
                losses={"train": train_losses, "val": val_losses},
                cfg=cfg,
                class_names=train_ds.label_names,
                best=True,
            )
            print(f"  saved best_model.pth (val_loss {val_loss:.6f})")
        else:
            print(f"  kept previous best_model.pth (best val_loss {best_val:.6f})")
        (cfg.checkpoint_dir / "history.json").write_text(
            json.dumps(
                {
                    "config": config_payload(cfg, train_ds.label_names),
                    "epochs": history,
                    "best_val_loss": best_val,
                    "best_epoch": best_epoch,
                    "total_elapsed_seconds": time.perf_counter() - t0,
                    "train_images": len(train_ds),
                    "val_images": len(val_ds),
                    "train_histogram": train_hist,
                    "val_histogram": val_hist,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    total_elapsed = time.perf_counter() - t0
    print("TRAINING RUN COMPLETE")
    print(f"total_elapsed_seconds = {total_elapsed:.1f}")
    print(f"last checkpoint: {cfg.checkpoint_dir / 'last_model.pth'}")
    print(f"best checkpoint: {cfg.checkpoint_dir / 'best_model.pth'}")
    return {
        "history": history,
        "best_val_loss": best_val,
        "best_epoch": best_epoch,
        "total_elapsed_seconds": total_elapsed,
        "checkpoint_dir": str(cfg.checkpoint_dir),
        "train_images": len(train_ds),
        "val_images": len(val_ds),
        "train_histogram": train_hist,
        "val_histogram": val_hist,
    }


def run_smoke_test(cfg: TrainConfig, *, write_preview: bool) -> int:
    label_map = load_label_map()
    print(f"Loading training annotations (capped at {cfg.smoke_max_images} images)...")
    dataset = ClothingDetectionDataset(
        cfg.train_images,
        cfg.train_ann,
        label_map,
        max_images=cfg.smoke_max_images,
        skip_invalid=True,
    )
    print("Dataset loaded successfully")
    print()
    print("Train images:")
    print(dataset.total_images_in_json)
    print()
    print("Foreground classes:")
    print(NUM_FOREGROUND)
    print()
    print("Total classes:")
    print(NUM_CLASSES)
    print()
    print("Background class:")
    print(BACKGROUND_ID)
    print()
    print("Device:")
    print(cfg.device)
    print()
    print("Smoke-test subset:")
    print(len(dataset))
    print()

    image, target = dataset[0]
    n = int(target["labels"].shape[0])
    names = [dataset.label_names[int(i) - 1] for i in target["labels"].tolist()]
    print("Sample image:")
    print(dataset.records[0]["path"])
    print()
    print("Image size:")
    print(tuple(image.shape))
    print()
    print("Number of instances:")
    print(n)
    print()
    print("Labels:")
    print(target["labels"].tolist())
    print(names)
    print()
    print("Boxes shape:")
    print(tuple(target["boxes"].shape))
    print()
    print("Masks shape:")
    print(tuple(target["masks"].shape))
    print()
    if dataset.instance_diagnostics:
        print("Instance diagnostics (invalid rows skipped, not invented):")
        for line in dataset.instance_diagnostics[:12]:
            print(f"  {line}")
        print()

    if write_preview:
        written = write_previews(dataset, PREVIEW_DIR, max_images=min(5, len(dataset)))
        print(f"Wrote {written} preview overlays to {PREVIEW_DIR}")
        print()

    loader = DataLoader(
        dataset,
        batch_size=cfg.batch_size,
        shuffle=False,
        num_workers=cfg.num_workers,
        collate_fn=collate_fn,
    )
    cfg.pretrained = True
    cfg.cpu_fast = True
    model, source = instantiate_model(cfg)
    model.to(cfg.device)
    model.train()
    box_classes, mask_classes = head_class_counts(model)
    print(f"Mask R-CNN initialized ({source})")
    print(f"box predictor classes: {box_classes}")
    print(f"mask predictor classes: {mask_classes}")
    assert box_classes == NUM_CLASSES, box_classes
    assert mask_classes == NUM_CLASSES, mask_classes
    print()

    images, targets = next(iter(loader))
    images, targets = _to_device(images, targets, cfg.device)
    loss_dict = model(images, targets)
    print("Forward pass successful")
    for key in LOSS_KEYS:
        value = loss_dict[key]
        print(f"{key} = {float(value.detach().cpu()):.6f}")
        if not _finite(value):
            raise RuntimeError(f"{key} is not finite: {value}")
    total_loss = sum(loss_dict.values())
    print()
    print(f"total_loss = {float(total_loss.detach().cpu()):.6f}")
    if not _finite(total_loss):
        raise RuntimeError(f"total_loss is not finite: {total_loss}")
    print()

    optimizer = make_optimizer(model, cfg)
    optimizer.zero_grad(set_to_none=True)
    total_loss.backward()
    print("Backward pass successful")
    optimizer.step()
    print("Optimizer step successful")
    print()
    print("SMOKE TEST PASSED")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mask R-CNN training (smoke test or small run)")
    parser.add_argument("--smoke-test", action="store_true", help="One-batch check, then exit.")
    parser.add_argument("--no-preview", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--epochs", type=int, default=DEFAULT_SMALL_EPOCHS)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--lr", type=float, default=0.005)
    parser.add_argument("--weight-decay", type=float, default=0.0005)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--device", default="auto", help="auto, cpu, or cuda")
    parser.add_argument("--checkpoint-dir", type=Path, default=CHECKPOINT_DIR)
    parser.add_argument("--max-train-images", type=int, default=None)
    parser.add_argument("--max-val-images", type=int, default=None)
    parser.add_argument("--min-size", type=int, default=None)
    parser.add_argument("--max-size", type=int, default=None)
    parser.add_argument("--print-every", type=int, default=10)
    parser.add_argument("--resume", type=Path, default=None, help="Continue training (loads optimizer + epoch).")
    parser.add_argument(
        "--init-from",
        type=Path,
        default=None,
        help="Load model weights only and start a fresh run (epoch 1, new optimizer). Prefer over --resume for transfer.",
    )
    parser.add_argument("--no-pretrained", action="store_true")
    parser.add_argument("--class-aware-subset", action="store_true", help="Greedy rare-class cover instead of first-N JSON rows.")
    parser.add_argument(
        "--weak-class-subset",
        action="store_true",
        help="Same M4.10 train subset: prefer shirt/scarf/belt/watch/skirt, keep the other classes, no duplicate images.",
    )
    parser.add_argument("--score-threshold", type=float, default=0.5, help="Stored for evaluation; not applied during SGD.")
    parser.add_argument(
        "--allow-full",
        action="store_true",
        help="Train on every image in the split. Off by default to protect CPU runs.",
    )
    parser.add_argument(
        "--train-id-list",
        type=Path,
        default=None,
        help="JSON list of train image ids. Does not edit the original dataset.",
    )
    parser.add_argument(
        "--hflip-prob",
        type=float,
        default=0.0,
        help="Probability of a horizontal flip on training images only.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    device = select_device(args.device)
    if args.smoke_test:
        cfg = default_config(smoke=True, device=device)
        cfg.seed = args.seed
        cfg.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        set_seed(cfg.seed)
        print("Mask R-CNN smoke test (no full training, no production model overwrite)")
        print(f"checkpoint directory (unused in smoke test): {cfg.checkpoint_dir}")
        print()
        return run_smoke_test(cfg, write_preview=not args.no_preview)

    cfg = default_config(smoke=False, device=device)
    cfg.seed = args.seed
    cfg.num_epochs = args.epochs
    cfg.batch_size = args.batch_size
    cfg.learning_rate = args.lr
    cfg.weight_decay = args.weight_decay
    cfg.num_workers = args.num_workers
    cfg.checkpoint_dir = Path(args.checkpoint_dir)
    cfg.pretrained = not args.no_pretrained
    cfg.print_every = args.print_every
    cfg.hflip_prob = args.hflip_prob
    if args.train_id_list is not None:
        id_path = Path(args.train_id_list)
        cfg.train_image_ids = {int(i) for i in json.loads(id_path.read_text(encoding="utf-8"))}
        cfg.subset_mode = "id_list"
        cfg.val_subset_mode = "class_aware"
    elif args.weak_class_subset:
        cfg.subset_mode = "weak_class"
        cfg.val_subset_mode = "class_aware"
    else:
        cfg.subset_mode = "class_aware" if args.class_aware_subset else "first"
        cfg.val_subset_mode = cfg.subset_mode
    cfg.score_threshold = args.score_threshold
    if args.min_size is not None:
        cfg.min_size = args.min_size
    if args.max_size is not None:
        cfg.max_size = args.max_size
    if args.allow_full:
        cfg.max_train_images = args.max_train_images
        cfg.max_val_images = args.max_val_images
    else:
        cfg.max_train_images = args.max_train_images if args.max_train_images is not None else DEFAULT_SMALL_TRAIN
        cfg.max_val_images = args.max_val_images if args.max_val_images is not None else DEFAULT_SMALL_VAL
        print(
            "Small-run safety cap is ON. "
            f"train_images<={cfg.max_train_images}, val_images<={cfg.max_val_images}. "
            "Pass --allow-full to use an entire split."
        )
    set_seed(cfg.seed)
    print("Mask R-CNN small training run (production inference unchanged)")
    if args.init_from is not None or args.resume is not None:
        # Heads already match the clothing checkpoint; skip COCO download when possible.
        cfg.pretrained = False
    run_training(cfg, resume=args.resume, init_from=args.init_from)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
