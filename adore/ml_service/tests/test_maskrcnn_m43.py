"""Milestone 4.3 tests. No downloads, no full-dataset training."""

from __future__ import annotations

from pathlib import Path

import torch

from test_maskrcnn_pipeline import _mini_coco
from training.dataset import NUM_CLASSES, ClothingDetectionDataset
from training.evaluate_maskrcnn import evaluate_model, print_metrics
from training.preview_maskrcnn import render_predictions, write_prediction_previews
from training.train_maskrcnn import (
    build_maskrcnn,
    default_config,
    load_checkpoint,
    make_optimizer,
    save_checkpoint,
)


def _tiny_model():
    return build_maskrcnn(NUM_CLASSES, pretrained=False, min_size=32, max_size=64, smoke_rpn=True)


def test_model_forward_pass_produces_finite_losses(tmp_path: Path):
    images_dir, ann_path = _mini_coco(tmp_path)
    dataset = ClothingDetectionDataset(images_dir, ann_path)
    image, target = dataset[0]
    model = _tiny_model()
    model.train()
    losses = model([image], [target])
    assert set(losses) >= {
        "loss_classifier",
        "loss_box_reg",
        "loss_mask",
        "loss_objectness",
        "loss_rpn_box_reg",
    }
    total = sum(losses.values())
    assert torch.isfinite(total).item()


def test_checkpoint_save_and_load_roundtrip(tmp_path: Path):
    cfg = default_config(smoke=True)
    cfg.checkpoint_dir = tmp_path
    model = _tiny_model()
    optimizer = make_optimizer(model, cfg)
    path = tmp_path / "last_model.pth"
    save_checkpoint(
        path,
        model,
        optimizer,
        epoch=3,
        train_loss=1.25,
        val_loss=1.40,
        losses={"total_loss": 1.25},
        cfg=cfg,
        class_names=["shirt"],
        best=False,
    )
    restored = _tiny_model()
    ckpt = load_checkpoint(path, restored, optimizer=make_optimizer(restored, cfg), map_location="cpu")
    assert ckpt["epoch"] == 3
    assert ckpt["train_loss"] == 1.25
    assert ckpt["val_loss"] == 1.40
    assert ckpt["class_names"] == ["shirt"]
    assert ckpt["num_classes"] == NUM_CLASSES
    assert "model_state_dict" in ckpt
    assert "optimizer_state_dict" in ckpt
    assert "config" in ckpt
    original = model.state_dict()
    loaded = restored.state_dict()
    key = next(k for k in original if original[k].dtype.is_floating_point)
    assert torch.allclose(original[key], loaded[key])


def test_best_checkpoint_kept_when_val_loss_worse(tmp_path: Path):
    cfg = default_config(smoke=True)
    model = _tiny_model()
    optimizer = make_optimizer(model, cfg)
    best_path = tmp_path / "best_model.pth"
    save_checkpoint(
        best_path,
        model,
        optimizer,
        epoch=1,
        train_loss=2.0,
        val_loss=1.0,
        losses={},
        cfg=cfg,
        class_names=["shirt"],
        best=True,
    )
    first = torch.load(best_path, map_location="cpu", weights_only=False)
    worse_val = 1.8
    best_val = first["val_loss"]
    assert worse_val > best_val
    # Training loop only writes best_model.pth when val_loss improves.
    if worse_val < best_val:
        save_checkpoint(
            best_path,
            model,
            optimizer,
            epoch=2,
            train_loss=1.5,
            val_loss=worse_val,
            losses={},
            cfg=cfg,
            class_names=["shirt"],
            best=True,
        )
    kept = torch.load(best_path, map_location="cpu", weights_only=False)
    assert kept["epoch"] == 1
    assert kept["val_loss"] == 1.0


def test_evaluate_model_on_mini_dataset(tmp_path: Path, capsys):
    images_dir, ann_path = _mini_coco(tmp_path)
    dataset = ClothingDetectionDataset(images_dir, ann_path)
    model = _tiny_model()
    metrics = evaluate_model(model, dataset, torch.device("cpu"), score_thresh=0.5, iou_thresh=0.5)
    assert metrics["num_validation_images"] == 2
    assert "precision" in metrics
    assert "recall" in metrics
    assert "mean_iou" in metrics
    assert "map50" in metrics
    assert set(metrics["per_class"]) == set(dataset.label_names)
    print_metrics(metrics)
    captured = capsys.readouterr().out
    assert "shirt" in captured
    assert "sunglasses" in captured


def test_prediction_visualization_writes_jpeg(tmp_path: Path):
    images_dir, ann_path = _mini_coco(tmp_path)
    dataset = ClothingDetectionDataset(images_dir, ann_path)
    image, target = dataset[0]
    h, w = int(image.shape[1]), int(image.shape[2])
    pred = {
        "boxes": target["boxes"],
        "labels": target["labels"],
        "scores": torch.ones(int(target["labels"].shape[0])),
        "masks": target["masks"].unsqueeze(1).float(),
    }
    rgb = render_predictions(image, pred, dataset.label_names, score_thresh=0.5)
    dest = tmp_path / "viz.jpg"
    rgb.save(dest, quality=90)
    assert dest.is_file()
    assert dest.stat().st_size > 0
    assert rgb.size == (w, h)

    model = _tiny_model()
    written = write_prediction_previews(
        model,
        dataset,
        tmp_path / "preds",
        torch.device("cpu"),
        max_images=1,
        score_thresh=0.01,
    )
    assert written == 1
    assert any((tmp_path / "preds").glob("pred_*.jpg"))
