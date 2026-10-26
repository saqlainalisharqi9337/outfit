# Milestone 4.6 — Larger Class-Aware Mask R-CNN Training Experiment

**MILESTONE 4.6 STATUS: PASS**

Controlled scaling run only. The M4.5 checkpoint was **not** overwritten. Full-dataset training was **not** started. FastAPI / YOLO / production inference / Flutter / the 15-class taxonomy were **not** modified. Mask R-CNN was **not** wired into the app.

This is **not** a production-ready detector. Success is defined as a completed experiment with valid artifacts and measurable improvement over M4.5.

## 1. Objective

Train a larger class-aware CPU subset (1000 train / 150 val / 5 epochs) without touching production, keep M4.5 weights intact, evaluate the **best** M4.6 checkpoint (not last), inspect prediction previews, and decide whether the extra data/epochs improved detection.

## 2. Exact training command

From `ml_service`:

```text
.\.venv\Scripts\python.exe -u training\train_maskrcnn.py --max-train-images 1000 --max-val-images 150 --epochs 5 --batch-size 1 --num-workers 0 --class-aware-subset --score-threshold 0.3 --checkpoint-dir ..\checkpoints\maskrcnn\m4_6
```

`--checkpoint-dir` is required so M4.5 `checkpoints/maskrcnn/best_model.pth` is not replaced. Training started from COCO-pretrained heads (no `--resume`). `--allow-full` was not passed. The small-run cap stayed on (`train_images<=1000`, `val_images<=150`).

Evaluation of the best M4.6 checkpoint (150 val images, score 0.5 / IoU 0.5):

```text
.\.venv\Scripts\python.exe -u -m training.evaluate_maskrcnn --checkpoint ..\checkpoints\maskrcnn\m4_6\best_model.pth --max-images 150 --preview-dir ..\outputs\maskrcnn_preview_m4_6 --metrics-json ..\checkpoints\maskrcnn\m4_6\eval_metrics.json
```

A matched 100-image prefix eval (same first-N val slice as M4.5) was also recorded at `checkpoints/maskrcnn/m4_6/eval_metrics_100.json` (`--no-preview`).

## 3. Dataset / subset information

| Setting | Value |
|---|---|
| train images in COCO JSON | 37887 |
| train subset used | **1000** |
| val images in COCO JSON | 1146 |
| val subset used (training) | **150** |
| subset mode | `class_aware` (seed 42) |
| eval images (official) | **150** first-N val JSON (not class-aware) |
| foreground classes | 15 |
| total classes | 16 (background id 0) |
| device | cpu |
| min_size / max_size | 256 / 320 |
| batch size / workers | 1 / 0 |
| lr / weight decay | 0.005 / 0.0005 |
| pretrained | COCO Mask R-CNN R50-FPN |
| stored score threshold | 0.3 (not applied during SGD) |

Subset stats: `checkpoints/maskrcnn/m4_6/subset_stats.json`.

## 4. Class distribution (training subset)

Instance counts **after** class-aware selection (1000 images):

| class | train instances | val-train subset instances |
|---|---:|---:|
| shirt | 209 | 27 |
| jacket | 332 | 43 |
| sweater | 88 | 13 |
| trousers | 355 | 39 |
| shorts | 120 | 24 |
| skirt | 140 | 28 |
| dress | 238 | 33 |
| jumpsuit | 77 | 12 |
| shoes | 1187 | 198 |
| bag | 281 | 57 |
| hat | 147 | 22 |
| belt | 234 | 28 |
| scarf | 101 | 13 |
| watch | 165 | 24 |
| sunglasses | 219 | 29 |

All 15 classes are present. Shoes remain the majority class (1187), but shirt/jacket/bag/belt/watch/sunglasses are no longer near-absent the way they were in the M4.3 first-N 100. Jumpsuit is still the rarest (77).

Official **evaluation** is first-N val JSON (150 images, 497 GT), which is still shoe-heavy (208 / 497 = 41.9% shoes). That matches M4.5’s first-N eval bias (138 / 325 = 42.5% shoes).

## 5. Epoch-by-epoch losses

From `checkpoints/maskrcnn/m4_6/history.json`. No steps skipped.

| Epoch | elapsed | train_loss | val_loss | checkpoint |
|---:|---:|---:|---:|---|
| 1 | 2022.9 s (33.7 min) | 1.704242 | **1.531695** | **best_model.pth saved** |
| 2 | 3436.2 s | 1.464350 | 1.595003 | previous best kept |
| 3 | 8805.5 s | 1.387056 | 1.533194 | previous best kept |
| 4 | 2251.7 s | 1.324713 | 1.619559 | previous best kept |
| 5 | 2360.1 s | 1.290070 | 1.683448 | previous best kept |

Train loss fell every epoch. Val loss was **best at epoch 1** and generally rose afterward (overfit on the 1000-image subset). Epoch 3 wall-clock was an outlier (machine load), not extra SGD steps.

**Training time:** `total_elapsed_seconds = 18880.5` (**5.24 hours**).

## 6. Best checkpoint

| | |
|---|---|
| path | `checkpoints/maskrcnn/m4_6/best_model.pth` |
| epoch | **1** |
| val_loss | **1.531695** |
| last checkpoint | `checkpoints/maskrcnn/m4_6/last_model.pth` (epoch 5, **not** used for eval) |
| M4.5 best (untouched) | `checkpoints/maskrcnn/best_model.pth` (351,651,352 bytes, LastWriteTime 2026-09-21 03:44:09) |

Eval used the M4.6 **best** file, not last.

## 7. Evaluation metrics (official: 150 val images)

Score **0.5**, IoU **0.5**. Source: `checkpoints/maskrcnn/m4_6/eval_metrics.json`.

| metric | value |
|---|---|
| validation images | 150 |
| predictions | **201** |
| ground-truth instances | **497** |
| confidence threshold | **0.5** |
| IoU threshold | **0.5** |
| precision | **0.7811** |
| recall | **0.3159** |
| mean IoU (TP) | **0.7697** |
| mAP@50 | **0.2879** |
| mAP@50:95 | **0.1462** |

157 TP / 44 FP / 340 FN at this operating point.

Matched 100-image prefix (same 325 GT as M4.5): P=0.7442, R=0.2954, mAP@50=0.2592, mAP@50:95=0.1356, mean IoU=0.7736, 129 predictions.

## 8. Complete per-class metrics (150 images, score 0.5 / IoU 0.5)

AP@50 is ranking-based (all scored detections). P/R/TP/FP/FN are at confidence 0.5.

| class | n_gt | tp | fp | fn | P | R | AP50 |
|---|---:|---:|---:|---:|---:|---:|---:|
| shirt | 16 | 0 | 0 | 16 | 0.000 | 0.000 | 0.348 |
| jacket | 31 | 1 | 0 | 30 | 1.000 | 0.032 | 0.440 |
| sweater | 1 | 0 | 0 | 1 | 0.000 | 0.000 | 0.031 |
| trousers | 38 | 22 | 14 | 16 | 0.611 | 0.579 | 0.586 |
| shorts | 17 | 9 | 3 | 8 | 0.750 | 0.529 | 0.554 |
| skirt | 14 | 0 | 0 | 14 | 0.000 | 0.000 | 0.220 |
| dress | 67 | 6 | 0 | 61 | 1.000 | 0.090 | 0.735 |
| jumpsuit | 6 | 0 | 0 | 6 | 0.000 | 0.000 | 0.038 |
| shoes | 208 | 119 | 27 | 89 | 0.815 | 0.572 | 0.608 |
| bag | 24 | 0 | 0 | 24 | 0.000 | 0.000 | 0.101 |
| hat | 9 | 0 | 0 | 9 | 0.000 | 0.000 | 0.252 |
| belt | 30 | 0 | 0 | 30 | 0.000 | 0.000 | 0.033 |
| scarf | 8 | 0 | 0 | 8 | 0.000 | 0.000 | 0.000 |
| watch | 11 | 0 | 0 | 11 | 0.000 | 0.000 | 0.000 |
| sunglasses | 17 | 0 | 0 | 17 | 0.000 | 0.000 | 0.372 |

Strong at 0.5: **shoes**, **trousers**, **shorts**. Dress/jacket are precise when they fire but very conservative. Shirt has a real ranked signal (AP 0.348) with **0** TP at 0.5. Scarf and watch remain AP 0.000.

## 9. M4.5 vs M4.6 comparison

| | M4.5 | M4.6 official | M4.6 matched 100 |
|---|---|---|---|
| train / val / epochs | 500 / 100 / 3 | 1000 / 150 / 5 | same weights |
| subset | class-aware | class-aware | class-aware |
| eval images | 100 first-N | **150** first-N | **100** first-N |
| score / IoU | 0.5 / 0.5 | 0.5 / 0.5 | 0.5 / 0.5 |
| predictions | 189 | 201 | 129 |
| GT | 325 | 497 | **325** |
| precision | 0.556 | **0.781** | **0.744** |
| recall | 0.323 | 0.316 | 0.295 |
| mAP@50 | 0.232 | **0.288** | **0.259** |
| mAP@50:95 | 0.093 | **0.146** | **0.136** |
| mean IoU (TP) | 0.740 | **0.770** | **0.774** |
| best val_loss | 1.754 (epoch 2) | **1.532** (epoch 1) | — |
| train time | 43.7 min | 5.24 h | — |

**M4.6 improved the detector** on the metrics that define this milestone: mAP@50, mAP@50:95, precision, and mask IoU of true positives. Recall at 0.5 is flat-to-slightly down because the model fires fewer, cleaner boxes (129 vs 189 on the matched 100).

Per-class (150-image M4.6 vs 100-image M4.5; AP is the fairest cross-set column):

| class | M4.5 AP50 | M4.6 AP50 (150) | note at score 0.5 |
|---|---:|---:|---|
| shirt | 0.099 | **0.348** | still 0 TP |
| jacket | 0.358 | **0.440** | TP 11→1 (scores often below 0.5) |
| sweater | 0.000 | 0.031 | still 0 TP (`n_gt=1`) |
| trousers | 0.505 | **0.586** | recall 0.28→0.58 |
| shorts | 0.465 | **0.554** | **0→9 TP** (now fires at 0.5) |
| skirt | 0.127 | **0.220** | 3 TP / 14 FP → 0/0 (less noisy) |
| dress | 0.706 | **0.735** | P 1.00 but recall 0.20→0.09 |
| jumpsuit | 0.057 | 0.038 | still 0 TP |
| shoes | 0.528 | **0.608** | P 0.60→0.82, R ~0.53→0.57 |
| bag | 0.138 | 0.101 | still 0 TP |
| hat | 0.190 | **0.252** | still 0 TP |
| belt | 0.053 | 0.033 | still 0 TP |
| scarf | 0.044 | **0.000** | still 0 TP |
| watch | 0.000 | 0.000 | still 0 TP |
| sunglasses | 0.216 | **0.372** | 2 TP → 0 TP at 0.5 |

## 10. Preview observations

Eight overlays in `outputs/maskrcnn_preview_m4_6/` (drawn at score ≥ 0.3). Same first-N val images as M4.5 previews.

- **Separate pieces:** yes, when both fire. `pred_02` trousers + one shoe; `pred_03` trousers + one shoe; `pred_06` jacket 0.44 + trousers 0.57.
- **Duplicate detections:** still present — two overlapping `trousers` boxes (0.39 and 0.64) in `pred_02`.
- **Dress vs shirt:** `pred_01` is a clean `dress 0.69` with **no** extra shirt tag (M4.5 tagged that mini-dress `shirt 0.35`).
- **Shorts vs skirt:** `pred_05` shorts 0.36 and `pred_07` shorts 0.65 are labeled shorts, not skirt (M4.5 put `skirt` on shorts in `pred_05`).
- **Trousers vs shirt:** not observed in these eight. Trousers masks attach to jeans/pants, not tops.
- **Jacket vs shirt:** leather jacket in `pred_06` is `jacket`, not shirt. The open shirt in `pred_05` is **missed** (M4.5 duplicated `jacket` on it).
- **Bag:** pink runway bag (`pred_01`) and large straw bag (`pred_06`) both missed.
- **Hat:** false `hat 0.33` on hair/`pred_00`; real red beanie in `pred_07` missed.
- **Belt:** obvious runway belt in `pred_02` missed.
- **Scarf / watch:** not detected in this preview set.
- **Sunglasses:** visible in `pred_00` and `pred_04`, not boxed.
- **Shoe false positives:** `pred_04` places `shoes 0.35` on the plaid jacket/hip, not the boots. The M4.5 door-handle-as-shoes in `pred_00` **did not** repeat.
- **Mask quality:** dress (`pred_01`) and shorts (`pred_05`, `pred_07`) follow the garment reasonably. Trousers in `pred_02` leak into the audience; jacket mask in `pred_06` is incomplete and ragged.
- **Missed objects:** jackets, shirts, bags, hats, belts, second shoes of a pair, sunglasses.
- **Small objects:** watch/sunglasses/belt still fail at 0.3–0.5. CPU `min_size=256` is a likely contributor.

## 11. Remaining weaknesses

1. Best epoch was **1 of 5** — extra epochs overfit; last.pt must not be deployed.
2. Accessories (bag, hat, belt, scarf, watch, sunglasses) still have **0 TP at 0.5**.
3. Shirt / sweater / jumpsuit / skirt still have 0 TP at 0.5 on the 150-image eval.
4. Jacket ranking improved (AP 0.36→0.44) but the 0.5 operating point is too strict (1 TP / 31 GT).
5. Dress is high-precision, low-recall.
6. Duplicate overlapping boxes remain (trousers).
7. Pair-wise shoes: often one shoe of two.
8. First-N val eval is still ~42% shoes, so headline mAP is shoe-influenced.
9. 256×320 CPU crops limit small-object learning.

Do **not** change the 15-class taxonomy from these errors.

## 12. Did the larger class-aware subset improve coverage?

**Yes, measurably, with class-specific caveats.**

Coverage gains vs M4.5: shorts now detect at 0.5; trousers recall roughly doubled; shoes are more precise; shirt/hat/sunglasses AP rose; skirt false positives collapsed; dress/shirt preview confusion improved.

Coverage still missing at the 0.5 operating point: shirt, bag, hat, belt, scarf, watch, jumpsuit, sweater, and (on this slice) skirt/sunglasses. Jacket is under-fired at 0.5 despite better AP.

## 13. Recommendation for the next milestone

Additional **capped** training is justified. Additional **epochs on this same 1000-image subset** are not — val loss already rose after epoch 1.

Do **not**: integrate Mask R-CNN into FastAPI or Flutter; train the full 37,887-image split on CPU; overwrite M4.5 or M4.6 best; change the taxonomy.

Suggested M4.7 (still isolated, class-aware):

```text
.\.venv\Scripts\python.exe -u training\train_maskrcnn.py --max-train-images 2000 --max-val-images 200 --epochs 3 --batch-size 1 --num-workers 0 --class-aware-subset --score-threshold 0.3 --lr 0.002 --resume ..\checkpoints\maskrcnn\m4_6\best_model.pth --checkpoint-dir ..\checkpoints\maskrcnn\m4_7
```

Evaluate `m4_7/best_model.pth` (not last) at score 0.5 and optionally 0.3, on at most 200 val images. If a GPU is available, raise `min_size` toward 800 before considering a larger CPU pass.

## Status

Training completed, M4.5 weights preserved, best M4.6 checkpoint evaluated, previews written, metrics recorded.

**MILESTONE 4.6 STATUS: PASS**
