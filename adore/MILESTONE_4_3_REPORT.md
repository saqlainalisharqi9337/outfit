# Milestone 4.3 — First Real Mask R-CNN Training and Validation

Verified on 2026-09-21. Production FastAPI / YOLO / gate inference was not modified. The taxonomy was not changed.

**MILESTONE 4.3 STATUS: PASS**

This is a **pipeline** pass, not a production detector. One CPU epoch on 100 images is not enough to ship instance segmentation.

## 1. Environment

- Python: 3.12.10 (`ml_service\.venv\Scripts\python.exe`)
- PyTorch: 2.13.0+cpu
- TorchVision: 0.28.0+cpu
- CUDA: False
- Device: **cpu**

M4.2 smoke test was re-run **before** any M4.3 code changes:

```text
.\.venv\Scripts\python.exe -u training\train_maskrcnn.py --smoke-test
```

Result: **SMOKE TEST PASSED**. Images, COCO boxes/masks, labels 1–15, tensor shapes, finite losses, backward pass, and 16-class heads all checked out.

## 2. Dataset size used

Full converted set remains 37,887 / 1,146 / 5,227 (train / val / test).

This experiment used a **capped subset** (safety cap; `--allow-full` was not passed):

| Split | Images used | COCO JSON size |
|---|---:|---:|
| train | **100** | 37,887 |
| val | **50** | 1,146 |

Train-subset instance counts (not balanced):

| class | count | class | count |
|---|---:|---|---:|
| shoes | 139 | dress | 53 |
| jacket | 27 | trousers | 23 |
| bag | 19 | skirt | 13 |
| belt | 12 | shirt | 9 |
| sunglasses | 9 | hat | 8 |
| shorts | 7 | watch | 5 |
| scarf | 4 | jumpsuit | 2 |
| sweater | 1 |  |  |

Val-subset ground truth: **154** instances over 50 images. `sweater` and `scarf` had **0** val GT in this slice.

## 3. Number of classes

15 foreground clothing classes + background = **16**. Mapping from `ml_service/taxonomy/unified_label_map.json`. Color is not part of the class name.

## 4. Training configuration

Command (from `ml_service`):

```text
.\.venv\Scripts\python.exe -u training\train_maskrcnn.py --max-train-images 100 --max-val-images 50 --epochs 1 --batch-size 1 --num-workers 0 --print-every 10
```

| Setting | Value |
|---|---|
| architecture | `maskrcnn_resnet50_fpn` + COCO V1 backbone, heads replaced for 16 classes |
| epochs | 1 |
| batch size | 1 |
| lr | 0.005 |
| weight decay | 0.0005 |
| workers | 0 |
| min_size / max_size | 256 / 320 (CPU) |
| seed | 42 |
| checkpoint dir | `checkpoints/maskrcnn/` |

## 5. Epoch results

One epoch. No skipped batches. Wall time **351.2 s** (~5.9 min).

## 6. Loss results

Train loss fell during the epoch (running mean `total` 2.65 at step 10 → **1.76** at step 100).

| | train | val |
|---|---:|---:|
| total | 1.763652 | 1.694521 |
| loss_classifier | 0.468276 | 0.381061 |
| loss_box_reg | 0.238507 | 0.280728 |
| loss_mask | 0.608161 | 0.594351 |
| loss_objectness | 0.270967 | 0.170654 |
| loss_rpn_box_reg | 0.177741 | 0.267728 |

Finite throughout. This is **not** evidence of a good detector — only that SGD ran.

## 7. Validation results

Checkpoint `checkpoints/maskrcnn/best_model.pth` was loaded by `training/evaluate_maskrcnn.py` (reload succeeded).

Official operating point **score ≥ 0.5**, IoU ≥ 0.5, 50 val images:

| metric | value |
|---|---|
| validation images | 50 |
| predictions | **0** |
| ground-truth instances | 154 |
| precision | 0.000 |
| recall | 0.000 |
| mean IoU (TP) | 0.000 |
| mAP@50 | 0.043 |
| mAP@50:95 | 0.013 |

After one epoch the heads almost never produce score ≥ 0.5. Ranking-based mAP@50 is still non-zero because AP uses the full scored list.

Low-threshold diagnostic **score ≥ 0.05**, IoU ≥ 0.5 (same 50 images):

| metric | value |
|---|---|
| predictions | 598 |
| precision | 0.100 |
| recall | 0.390 |
| mean IoU (matched TP) | 0.655 |
| mAP@50 | 0.043 |
| mAP@50:95 | 0.013 |

Commands:

```text
.\.venv\Scripts\python.exe -u training\evaluate_maskrcnn.py --checkpoint ..\checkpoints\maskrcnn\best_model.pth --max-images 50 --preview-count 8 --score-threshold 0.5
.\.venv\Scripts\python.exe -u training\evaluate_maskrcnn.py --checkpoint ..\checkpoints\maskrcnn\best_model.pth --max-images 50 --preview-count 8 --score-threshold 0.05 --metrics-json ..\checkpoints\maskrcnn\eval_metrics_score005.json
```

## 8. Per-class results

At score 0.5 every class has TP=0. At score 0.05 (honest low-threshold counts; AP@50 is threshold-free):

| class | n_gt | tp | fp | fn | P | R | AP50 |
|---|---:|---:|---:|---:|---:|---:|---:|
| shirt | 4 | 0 | 0 | 4 | 0.000 | 0.000 | 0.000 |
| jacket | 9 | 5 | 94 | 4 | 0.051 | 0.556 | 0.038 |
| sweater | 0 | 0 | 0 | 0 | 0.000 | 0.000 | 0.000 |
| trousers | 9 | 0 | 2 | 9 | 0.000 | 0.000 | 0.000 |
| shorts | 8 | 0 | 0 | 8 | 0.000 | 0.000 | 0.000 |
| skirt | 5 | 0 | 9 | 5 | 0.000 | 0.000 | 0.000 |
| dress | 23 | 17 | 114 | 6 | 0.130 | 0.739 | 0.230 |
| jumpsuit | 2 | 0 | 0 | 2 | 0.000 | 0.000 | 0.000 |
| shoes | 65 | 38 | 319 | 27 | 0.106 | 0.585 | 0.380 |
| bag | 7 | 0 | 0 | 7 | 0.000 | 0.000 | 0.000 |
| hat | 3 | 0 | 0 | 3 | 0.000 | 0.000 | 0.000 |
| belt | 10 | 0 | 0 | 10 | 0.000 | 0.000 | 0.000 |
| scarf | 0 | 0 | 0 | 0 | 0.000 | 0.000 | 0.000 |
| watch | 3 | 0 | 0 | 3 | 0.000 | 0.000 | 0.000 |
| sunglasses | 6 | 0 | 0 | 6 | 0.000 | 0.000 | 0.000 |

Poor classes are **not** hidden. Shoes and dress dominate because they dominate the 100-image train slice. Shirt, trousers, shorts, skirt, bag, hat, belt, watch, sunglasses, jumpsuit are effectively unused by the current weights.

## 9. Prediction preview location

`outputs/maskrcnn_preview/` (8 val overlays, source images unchanged):

- `pred_00_7fc8a54146a81b33f348f21ad07fa141.jpg`
- `pred_01_5f1a6fc913ba40dee4d94b3428afba15.jpg`
- `pred_02_c201083bb1f8b26dba075f380aa799bc.jpg`
- `pred_03_d36482dcef46afcfcb7d96013c0715c2.jpg`
- `pred_04_50ab7c8b2848817931e5879671e234ae.jpg`
- `pred_05_7cec6c9dbd406032c6069f32381f2daa.jpg`
- `pred_06_fad1a9c9583ecdcf383d47d322fbc53a.jpg`
- `pred_07_99e576a9859dbbfa7bbf1ca6a8200960.jpg`

Previews currently use score ≥ 0.05 so boxes/masks are visible. At 0.3–0.5 most images were empty except an occasional `shoes` box (~0.43–0.46).

## 10. Observed errors

Inspected the eight previews. **Do not change the taxonomy from this evidence.**

- **Missed objects:** shirt, sunglasses, bag, hat, belt, trousers, shorts are routinely absent even when obvious (suit + shirt + glasses; runway dress + pink bag; leather jacket + basket + jeans; red beanie + shorts).
- **Incorrect classes:** a suit torso tagged `dress`; a black mini-dress also tagged `jacket`; jeans tagged as `dress`; a hat region swallowed into a `dress` box. This is the same dress-vs-everything failure mode the project already sees in classification, now at instance level and with **low confidence**.
- **Overlapping objects:** jacket and dress boxes stacked on the same torso; multiple overlapping `dress` masks on one person.
- **Incorrect masks:** ragged, partial coverage of jackets/dresses; shoe masks sometimes cover a door handle or empty floor.
- **Incorrect boxes:** tiny `shoes` boxes on door hardware and background (`pred_00`).
- **Duplicate detections:** many repeated `shoes` boxes on one image (`pred_06`).
- **Low confidence:** almost all scores are 0.05–0.17; nothing at the 0.5 operating point.
- **Similar-class confusion (project-relevant):**
  - shirt vs t-shirt: t-shirt is still DATA REQUIRED / not a detector class. The model simply failed to predict `shirt`.
  - jacket vs hoodie: hoodie is not in the 15-class set. Jacket recall exists only at low score and with huge FP.
  - trousers vs skirt: trousers AP=0; skirt AP=0 with 9 FP / 0 TP.
  - dress vs skirt: dress fires on whole-body regions including shorts (`pred_07`).
  - footwear: only `shoes` fires, with many duplicates and missed second shoes.
  - bags/accessories: bag/hat/belt/watch/sunglasses AP=0 in this run.
  - overlapping garments: instances are not cleanly separated yet.

These are **underfitting + class imbalance + one epoch on CPU**, not a reason to collapse classes.

## 11. Checkpoint location

`checkpoints/maskrcnn/`

- `best_model.pth` (351,651,224 bytes) — lowest val loss so far (1.694521)
- `last_model.pth` — same after a single epoch
- `history.json`
- `eval_metrics.json` (score 0.5)
- `eval_metrics_score005.json` (score 0.05)

Each `.pth` stores `model_state_dict`, `optimizer_state_dict`, `epoch`, `train_loss`, `val_loss`, `class_names`, and `config`. Best is only overwritten when val loss improves. Evaluate successfully loaded `best_model.pth`.

## 12. Tests executed

```text
.\.venv\Scripts\python.exe -m pytest tests/test_maskrcnn_pipeline.py tests/test_maskrcnn_m43.py -q
```

**11 passed** (6 existing M4.2 + 5 M4.3). No downloads. Coverage includes dataset targets, masks/boxes/labels, 16-class heads, finite training losses, checkpoint save/load, best-ckpt retention, evaluator execution, and prediction JPEG writing.

## 13. Ready for the next milestone?

**The training/eval/checkpoint pipeline is ready for a larger M4.4 run.**

**The weights are not ready to replace production recognition.**

Do not wire this checkpoint into FastAPI. Do not treat mAP@50 = 0.04 as a product metric. Next training should keep the 15-class taxonomy, increase images/epochs (ideally GPU), and re-evaluate dress/skirt/shoes/bag errors with a real score threshold.

### Files created / modified

Created: `tests/test_maskrcnn_m43.py`, `checkpoints/maskrcnn/`, `outputs/maskrcnn_preview/`, `MILESTONE_4_3_REPORT.md`

Modified: `training/train_maskrcnn.py`, `training/evaluate_maskrcnn.py`, `training/preview_maskrcnn.py`, `training/README.md`, `.gitignore`

Production inference files were not modified.
