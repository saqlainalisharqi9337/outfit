# Milestone 4.2 — Mask R-CNN Training Pipeline

Verified on 2026-09-21 using `ml_service\.venv\Scripts\python.exe`.
Full training was **not** started. Production inference was not modified.

**Result: SMOKE TEST PASSED**

## Repository inspection

Inspected before writing training code:

- `ml_service/taxonomy/unified_label_map.json` — 15 detector classes; `class_id` is 1-based
- `ml_service/training/label_map.py` — existing taxonomy loader (reused)
- `ml_service/training/prepare_detection_dataset.py` — COCO conversion utilities
- `ml_service/training/visualize_detection_dataset.py` — overlay palette (reused)
- `ml_service/training/audit_detection_dataset.py`
- `ml_service/pytest.ini` — `pythonpath = .`, `testpaths = tests`
- `ml_service/tests/conftest.py` — FastAPI detector reset only; training tests still run
- TorchVision 0.28.0+cpu: `maskrcnn_resnet50_fpn`, weights enum is **only** `MaskRCNN_ResNet50_FPN_Weights.COCO_V1`
- No existing `dataset.py`, `train_maskrcnn.py`, or `evaluate_maskrcnn.py`

Production files were not opened for edit: `clothing_classifier.py`, YOLO detector, `*_gate.py`, `*.keras`, FastAPI `/analyze-clothing`, recommendation engine, Flutter app.

## Dataset paths

Root: `ml_service/datasets/clothing_detection/`

| Split | Images | Annotations |
|---|---|---|
| train | `ml_service/datasets/clothing_detection/images/train/` | `ml_service/datasets/clothing_detection/annotations/instances_train.json` |
| val | `ml_service/datasets/clothing_detection/images/val/` | `ml_service/datasets/clothing_detection/annotations/instances_val.json` |
| test | `ml_service/datasets/clothing_detection/images/test/` | `ml_service/datasets/clothing_detection/annotations/instances_test.json` |

COCO JSON image counts used by the loader: train **37887**, val **1146**, test **5227**.

## Taxonomy

Source of truth: `ml_service/taxonomy/unified_label_map.json`

- Background = **0**
- Foreground = **15** (`shirt` … `sunglasses`)
- Total Mask R-CNN classes = **16**
- Dataset `category_id` values are mapped through this file to labels **1–15**
- Color is not part of the class name (no `red_shirt` / `blue_shirt`)

## Dataset loader

`ml_service/training/dataset.py` — `ClothingDetectionDataset`

- Lazy image load (`PIL` → CHW float tensor in `[0, 1]`)
- One target dict per image: `boxes`, `labels`, `masks`, `image_id`, `area`, `iscrowd`
- Instances are **not** merged (shirt + trousers + shoes + bag → four targets)
- `collate_fn` returns `(images, targets)` so `N` can differ across the batch
- Invalid instances are skipped with diagnostics; fake box-masks are never invented
- Smoke mode caps records with `max_images` (default 4); the COCO JSON is still the train split

## Mask handling

Uses the real COCO `segmentation` field:

- **Polygons** → binary mask via `PIL.ImageDraw.polygon`
- **Uncompressed RLE** (`counts` as a list) → Fortran-order decode
- **Compressed RLE** (`counts` as a COCO string) → `rleFrString`-compatible decode, then Fortran-order

No pycocotools. No box-shaped fake masks. No full-image masks.

Validated: `mask.shape == (H, W)` of the image, and `N` matches boxes and labels. Boxes must satisfy `x1 < x2`, `y1 < y2`, positive size, and lie inside the image. Labels must be in `1..15`.

## Model architecture

`torchvision.models.detection.maskrcnn_resnet50_fpn`

Smoke test loaded **pretrained COCO V1** weights (`maskrcnn_resnet50_fpn_coco-bf2d0c1e.pth`), then replaced the heads.

CPU smoke used `min_size=256`, `max_size=320`, `batch_size=1`, `num_workers=0`.

## Prediction heads

After replacement:

- `FastRCNNPredictor` — `cls_score.out_features = 16`
- `MaskRCNNPredictor` — `mask_fcn_logits.out_channels = 16`

Asserted during smoke test and pytest. Original 91-class COCO heads are not left in place.

## Device

Automatic: CUDA if available, else CPU.

This machine: **cpu** (`torch 2.13.0+cpu`, `CUDA = False`).

## Smoke-test command

From `ml_service`:

```text
.\.venv\Scripts\python.exe -u -m training.train_maskrcnn --smoke-test
```

Equivalent file form:

```text
.\.venv\Scripts\python.exe training\train_maskrcnn.py --smoke-test
```

Running without `--smoke-test` is refused (exit code 2). No epochs. No 37,887-image pass. No checkpoint write.

## Smoke-test result

**SMOKE TEST PASSED** (one forward + backward + optimizer step).

```text
Dataset loaded successfully
Train images:
37887
Foreground classes:
15
Total classes:
16
Device:
cpu
Sample image:
...\images\train\3ce385855f07c77fdeb911ed15094c53.jpg
Image size:
(3, 1024, 682)
Number of instances:
3
Labels:
[9, 9, 7]
['shoes', 'shoes', 'dress']
Boxes shape:
(3, 4)
Masks shape:
(3, 1024, 682)
box predictor classes: 16
mask predictor classes: 16
Forward pass successful
loss_classifier = 2.903865
loss_box_reg = 0.038315
loss_mask = 1.404064
loss_objectness = 1.847449
loss_rpn_box_reg = 0.126554
total_loss = 6.320246
Backward pass successful
Optimizer step successful
SMOKE TEST PASSED
```

All listed losses were finite. No `best_model.pth` / `last_model.pth` / `smoke_test_model.pth` was written.

Previews (4 overlays, source images unchanged):

`evaluation_results/maskrcnn_pipeline_preview/`

- `smoke_preview_00_3ce385855f07c77fdeb911ed15094c53.jpg`
- `smoke_preview_01_47cbe3ead1617a9971dccc438a8e8884.jpg`
- `smoke_preview_02_361cc7654672860b1b7c85fe8e92b38a.jpg`
- `smoke_preview_03_8a20effd8b6ebcaf2b74caa7d35eee41.jpg`

## Tests

```text
.\.venv\Scripts\python.exe -m pytest tests/test_maskrcnn_pipeline.py -q
```

**6 passed** in 25.24s. No downloads. Coverage:

1. taxonomy has 15 foreground classes and background 0
2. dataset loads; image is a Tensor; target is a dict
3. boxes `[N,4]`, labels `[N]`, masks `[N,H,W]`, same `N`
4. labels in 1–15
5. collate works with different instance counts (4 vs 2)
6. box and mask predictors output 16 classes (`weights=None`, `weights_backbone=None`)

Evaluation skeleton (`python -m training.evaluate_maskrcnn`) printed planned metrics and processed **zero** validation images.

## Files created

- `ml_service/training/dataset.py`
- `ml_service/training/train_maskrcnn.py`
- `ml_service/training/preview_maskrcnn.py`
- `ml_service/training/evaluate_maskrcnn.py`
- `ml_service/tests/test_maskrcnn_pipeline.py`
- `ml_service/models/maskrcnn/.gitkeep`
- `evaluation_results/maskrcnn_pipeline_preview/*.jpg`
- `MILESTONE_4_2_REPORT.md`

## Files modified

- `.gitignore` — ignore `ml_service/models/maskrcnn/*.pth`
- `ml_service/training/README.md` — document the smoke-test command

## Known limitations

- CPU-only; smoke used a tiny subset (4 images) and reduced `min_size`
- The train COCO JSON is parsed once even in smoke mode (images stay lazy)
- Invalid instances are skipped with diagnostics rather than repaired
- mAP / precision / recall / per-class AP are **not** computed yet
- COCO pretrained weights (~170 MB) were downloaded into the local Torch hub cache for the smoke test; that file is not a production Adore checkpoint
- Color/pattern analysis remains a later stage after instance masks, not class labels

## Next step

Do **not** start full training.

Milestone 4.3 should add a real (still small, CPU-aware) training loop, checkpointing (`best_model.pth` / `last_model.pth`), and then evaluation. Until that milestone is approved, the only training command is the smoke test above.

The trainer currently refuses:

```text
.\.venv\Scripts\python.exe -m training.train_maskrcnn
```
