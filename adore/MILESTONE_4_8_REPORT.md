# Milestone 4.8 — Targeted Mask R-CNN Training Improvement

**MILESTONE 4.8 STATUS: PASS**

Controlled training experiment only. `checkpoints/maskrcnn/m4_6/best_model.pth` was **not** overwritten. FastAPI / YOLO / production gates / Flutter / the 15-class taxonomy / dataset labels were **not** modified. Mask R-CNN was **not** integrated into the app. The full 44k-image set was **not** trained. Score 0.10 is **not** a recommended operating point.

This is **not** a production-ready detector.

## 1. Objective

Improve the detector itself after M4.7’s mixed diagnosis (low-confidence garments plus small-object misses), by fine-tuning from the frozen M4.6 best checkpoint on a larger class-aware subset at a slightly higher input size.

## 2. Checkpoint initialization

Verified load before training (`epoch=1`, `best=True`, `val_loss=1.531695309082667`, 16 classes). SHA-256 of the source file: `3180B1EC3CA48444671C93FE7DC651BB54FD23922071670B8C959B2EB0BB4AF2`.

| field | value |
|---|---|
| initialization | `checkpoints/maskrcnn/m4_6/best_model.pth` (weights only) |
| optimizer | new (not copied from M4.6) |
| epoch counter | restarted at 1 |
| COCO pretrained start | **not** used |
| M4.8 output dir | `checkpoints/maskrcnn/m4_8/` |

`--init-from` loads weights and resets the optimizer. `--resume` was used only to finish the interrupted epoch 3 from `m4_8/last_model.pth` (epoch 2).

## 3. Training configuration

From `ml_service`:

```text
.\.venv_m48\Scripts\python.exe -u training\train_maskrcnn.py --max-train-images 2000 --max-val-images 250 --epochs 3 --batch-size 1 --num-workers 0 --class-aware-subset --score-threshold 0.5 --checkpoint-dir ..\checkpoints\maskrcnn\m4_8 --init-from ..\checkpoints\maskrcnn\m4_6\best_model.pth --min-size 320 --max-size 480 --print-every 50 --device cpu
```

Epoch 3 was resumed after an interrupt (the first attempt had reached about step 900/2000 and was not saved):

```text
.\.venv_m48\Scripts\python.exe -u training\train_maskrcnn.py --max-train-images 2000 --max-val-images 250 --epochs 3 --batch-size 1 --num-workers 0 --class-aware-subset --score-threshold 0.5 --checkpoint-dir ..\checkpoints\maskrcnn\m4_8 --resume ..\checkpoints\maskrcnn\m4_8\last_model.pth --min-size 320 --max-size 480 --print-every 100 --device cpu
```

| Setting | Value |
|---|---|
| train / val images | **2000 / 250** (class-aware, seed 42) |
| epochs | 3 |
| batch size / workers | 1 / 0 |
| learning rate / weight decay / momentum | 0.005 / 0.0005 / 0.9 |
| device | cpu |
| min_size / max_size | **320 / 480** (M4.6 was 256 / 320) |
| foreground classes | 15 (background id 0) |
| skipped steps | 0 |

The existing pipeline already had `--min-size` / `--max-size`. Resolution was raised one step above the M4.6 CPU setting (256/320), not to the GPU default (800/1333).

## 4. Class distribution (training subset)

Instance counts after class-aware selection. Annotations were not duplicated or relabeled. Source: `checkpoints/maskrcnn/m4_8/subset_stats.json`.

| class | train instances | val-subset instances |
|---|---:|---:|
| shirt | 443 | 45 |
| jacket | 660 | 74 |
| sweater | 180 | 21 |
| trousers | 732 | 72 |
| shorts | 229 | 38 |
| skirt | 279 | 47 |
| dress | 445 | 59 |
| jumpsuit | 161 | 20 |
| shoes | 2424 | 340 |
| bag | 558 | 85 |
| hat | 294 | 38 |
| belt | 458 | 49 |
| scarf | 196 | 24 |
| watch | 331 | 33 |
| sunglasses | 445 | 58 |

All 15 classes are present. Shoes are still the majority (2424). Watch (331), belt (458), bag (558), scarf (196), and hat (294) are all in the train subset. Jumpsuit is the rarest garment (161).

Official **evaluation** below is first-N val JSON (250 images), not this class-aware val subset. That matches how M4.5 (100) and M4.6 (150) were scored, but the image counts are **not** the same, so headline metrics are not a paired comparison.

## 5. Losses and checkpoint selection

| epoch | train_loss | val_loss | elapsed_seconds | checkpoint |
|---:|---:|---:|---:|---|
| 1 | 1.480714 | 1.363468 | 7935.4 | best at the time |
| 2 | 1.310789 | **1.283382** | 7620.8 | **best_model.pth** |
| 3 | 1.253248 | 1.294107 | 44255.6 | last only; previous best kept |

Best epoch is **2**, not the final epoch. Train loss fell every epoch. Val loss improved through epoch 2 and rose at epoch 3.

`history.json` `total_elapsed_seconds` (44256.2) is only the epoch-3 resume session. Sum of the three epoch times is **59811.8 s**.

Saved files:

- `checkpoints/maskrcnn/m4_8/best_model.pth` — epoch 2, `best=True`, val_loss 1.283382
- `checkpoints/maskrcnn/m4_8/last_model.pth` — epoch 3, `best=False`, val_loss 1.294107

## 6. Official evaluation (best checkpoint only)

Command (score 0.5, IoU 0.5, 250 first-N val images):

```text
.\.venv_m48\Scripts\python.exe -u -m training.evaluate_maskrcnn --checkpoint ..\checkpoints\maskrcnn\m4_8\best_model.pth --max-images 250 --score-threshold 0.5 --iou-threshold 0.5 --preview-dir ..\outputs\maskrcnn_preview_m4_8 --metrics-json ..\checkpoints\maskrcnn\m4_8\eval_metrics.json --device cpu
```

| metric | value |
|---|---:|
| validation images | 250 |
| predictions | 474 |
| ground-truth instances | 846 |
| precision | **0.738** |
| recall | **0.414** |
| mAP@50 | **0.350** |
| mAP@50:95 | **0.192** |
| mean IoU (TP) | **0.801** |

mAP here is the ranking AP used by M4.5/M4.6 (all scored detections). It matches the threshold script’s unfiltered ranking AP (`mAP@50=0.3498`, `mAP@50:95=0.1922`, 2176 raw predictions).

### Per-class at score 0.5 / IoU 0.5

AP50 in this table is ranking AP (same rule as M4.6 `eval_metrics.json`).

| class | n_gt | TP | FP | FN | P | R | AP50 |
|---|---:|---:|---:|---:|---:|---:|---:|
| shirt | 27 | 0 | 0 | 27 | 0.000 | 0.000 | 0.298 |
| jacket | 64 | 25 | 10 | 39 | 0.714 | 0.391 | 0.530 |
| sweater | 2 | 0 | 0 | 2 | 0.000 | 0.000 | 0.000 |
| trousers | 71 | 49 | 17 | 22 | 0.742 | 0.690 | 0.704 |
| shorts | 23 | 4 | 0 | 19 | 1.000 | 0.174 | 0.503 |
| skirt | 29 | 12 | 41 | 17 | 0.226 | 0.414 | 0.210 |
| dress | 110 | 72 | 23 | 38 | 0.758 | 0.655 | 0.751 |
| jumpsuit | 7 | 0 | 0 | 7 | 0.000 | 0.000 | 0.105 |
| shoes | 349 | 163 | 11 | 186 | 0.937 | 0.467 | 0.623 |
| bag | 43 | 11 | 14 | 32 | 0.440 | 0.256 | 0.270 |
| hat | 19 | 9 | 4 | 10 | 0.692 | 0.474 | 0.443 |
| belt | 43 | 1 | 2 | 42 | 0.333 | 0.023 | 0.105 |
| scarf | 13 | 0 | 0 | 13 | 0.000 | 0.000 | 0.005 |
| watch | 18 | 1 | 1 | 17 | 0.500 | 0.056 | 0.215 |
| sunglasses | 28 | 3 | 1 | 25 | 0.750 | 0.107 | 0.485 |

## 7. Threshold sweep

IoU = 0.5. Same 250 images. Artifact: `checkpoints/maskrcnn/m4_8/threshold_study.json`.

Operating-point P/R/TP/FP/FN use detections with score ≥ threshold. **mAP columns in this table are filtered** (detections ≥ that score). They are not the headline ranking AP in §6.

| score | n_pred | n_gt | TP | FP | FN | P | R | mAP@50 (filtered) | mAP@50:95 (filtered) | mean IoU TP |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.50 | 474 | 846 | 350 | 124 | 496 | 0.738 | 0.414 | 0.208 | 0.118 | 0.801 |
| 0.40 | 588 | 846 | 404 | 184 | 442 | 0.687 | 0.478 | 0.241 | 0.136 | 0.797 |
| 0.30 | 743 | 846 | 442 | 301 | 404 | 0.595 | 0.522 | 0.275 | 0.156 | 0.792 |
| 0.20 | 949 | 846 | 485 | 464 | 361 | 0.511 | 0.573 | 0.311 | 0.174 | 0.789 |

Score 0.10 was computed by the existing sweep script and is **not** recommended: P falls to 0.376 while FP rises to 895. Mean IoU of true positives stays about 0.79–0.80, so matched boxes already overlap well.

### Confidence (all raw detections)

| class | n | min | max | mean | median | &lt;0.5 | ≥0.5 |
|---|---:|---:|---:|---:|---:|---:|---:|
| shirt | 134 | 0.050 | **0.336** | 0.129 | 0.110 | 134 | **0** |
| jacket | 157 | 0.051 | 0.950 | 0.300 | 0.206 | 122 | 35 |
| sweater | 39 | 0.050 | 0.155 | 0.080 | 0.068 | 39 | 0 |
| bag | 238 | 0.050 | 0.988 | 0.221 | 0.123 | 213 | 25 |
| hat | 72 | 0.055 | 0.990 | 0.317 | 0.219 | 59 | 13 |
| belt | 151 | 0.050 | 0.582 | 0.151 | 0.107 | 148 | 3 |
| scarf | 92 | 0.050 | **0.121** | 0.074 | 0.070 | 92 | **0** |
| watch | 50 | 0.050 | 0.526 | 0.144 | 0.095 | 48 | 2 |
| sunglasses | 35 | 0.050 | 0.848 | 0.226 | 0.110 | 31 | 4 |

Shirt’s highest score on this slice is **0.336** (M4.7 reported 0.398 on the 150-image slice). No shirt box crosses 0.5. Scarf never exceeds 0.121.

### Per-GT diagnosis (best overlap, IoU 0.5)

| class | n_gt | score≥0.5 | score&lt;0.5 correct | wrong class | IoU&lt;0.5 | missed | reading |
|---|---:|---:|---:|---:|---:|---:|---|
| shirt | 27 | 0 | 17 | 4 | 5 | 1 | low confidence |
| jacket | 64 | 25 | 25 | 6 | 7 | 1 | mixed; many now ≥0.5 |
| sweater | 2 | 0 | 0 | 1 | 1 | 0 | n_gt too small to generalize |
| bag | 43 | 11 | 9 | 5 | 14 | 4 | mixed: some real TPs, many poor boxes |
| hat | 19 | 9 | 2 | 0 | 4 | 4 | mostly localized; leftover misses |
| belt | 43 | 1 | 15 | 2 | 11 | 14 | low confidence plus misses / weak boxes |
| scarf | 13 | 0 | 2 | 5 | 6 | 0 | wrong class or poor overlap; AP stays ~0 |
| watch | 18 | 1 | 5 | 1 | 4 | 7 | still mostly missed or weak |
| sunglasses | 28 | 3 | 12 | 0 | 2 | 11 | low confidence plus misses |

Focused wrong-class counts at IoU ≥ 0.5: jacket→shirt 1, shorts→skirt 1, scarf→belt 1. The large M4.7 confusion pairs are still rare. Skirt’s problem on this slice is false positives (41 FP vs 12 TP at 0.5), not a large shorts→skirt GT swap count.

## 8. Small-object evidence

| class | M4.6 at 0.5 (150 images) | M4.8 at 0.5 (250 images) | what the numbers support |
|---|---|---|---|
| watch | 0 / 11 TP | 1 / 18 TP | one high-confidence hit; 7/18 still fully missed |
| belt | 0 / 30 TP | 1 / 43 TP | still almost absent at 0.5; 14/43 missed, 11 poorly localized |
| sunglasses | 0 / 17 TP | 3 / 28 TP | a few ≥0.5; 12 more are correct but below 0.5; 11 missed |
| hat | 0 / 9 TP | 9 / 19 TP | clearest accessory gain at 0.5 |
| bag | 0 / 24 TP | 11 / 43 TP | real ≥0.5 detections; 14/43 still fail IoU |
| scarf | 0 / 8 TP, AP 0 | 0 / 13 TP, max score 0.121 | **not** improved |

These rows use different validation prefixes (150 vs 250). Direction is usable. A paired claim would need the same 150 images.

## 9. Preview observations

Eight overlays in `outputs/maskrcnn_preview_m4_8/` (drawn at score ≥ 0.3).

- **Separate pieces that look right:** jacket 0.73 + trousers 0.96 + one shoe 0.75 (`pred_02`); trousers 0.85 on the purple outfit (`pred_03`); dress 0.70 (`pred_01`); hat 0.83 (`pred_07`); jacket 0.85 + trousers 0.92 + bag 0.96 (`pred_06`).
- **Missed garments:** open shirt called `dress 0.39` inside a jacket (`pred_00`); plaid overshirt and shorts missed (`pred_04`); cardigan/top missed, two `bag` boxes on the torso (`pred_05`); white shirt under the leather jacket missed (`pred_06`); top called `dress 0.30` over a skirt (`pred_07`).
- **Duplicate / overlap:** two `shoes` boxes on the two feet (`pred_03`, 0.63 and 0.46); two overlapping `bag` boxes (`pred_05`); jacket box in `pred_06` covers the whole person while the mask is mostly the jacket.
- **Shorts/skirt:** purple shorts labeled `skirt 0.82` (`pred_05`); patterned shorts labeled `skirt 0.64` (`pred_07`). This matches the high skirt FP count.
- **Scarf:** none of the eight previews shows a scarf detection.
- **Small objects:** sunglasses 0.48 on the face (`pred_00`, below 0.5); belt on the tan jacket not boxed (`pred_02`); glasses in `pred_04` not boxed; one boot pair boxed, the other boot missed (`pred_04`).
- **Background FP:** door handle in `pred_00` is not labeled shoes (unlike an older M4.5 preview). No large background shoe box in these eight.
- **Masks:** jacket/dress/trousers masks follow the garment in `pred_02` and `pred_06`. The dress mask on the pink shirt (`pred_00`) and the bag masks on the cardigan (`pred_05`) are the wrong region.

## 10. Comparison

Val loss is **not** comparable across milestones: each run used a different class-aware val subset (100 / 150 / 250).

Detection metrics use first-N val JSON at score 0.5 / IoU 0.5. Image counts differ, so this is a directional comparison, not a paired test.

| | M4.5 | M4.6 | M4.8 |
|---|---:|---:|---:|
| train / val / epochs | 500 / 100 / 3 | 1000 / 150 / 5 | 2000 / 250 / 3 |
| init | COCO | COCO | M4.6 best (epoch 1) |
| min / max size | 256 / 320 | 256 / 320 | 320 / 480 |
| best epoch | 2 | 1 | **2** |
| best val_loss | 1.754 | 1.532 | **1.283** |
| eval images | 100 | 150 | 250 |
| GT instances | 325 | 497 | 846 |
| predictions | 189 | 201 | 474 |
| precision | 0.556 | **0.781** | 0.738 |
| recall | 0.323 | 0.316 | **0.414** |
| mAP@50 | 0.232 | 0.288 | **0.350** |
| mAP@50:95 | 0.093 | 0.146 | **0.192** |
| mean IoU (TP) | 0.740 | 0.770 | **0.801** |

Ranking AP50 (different slices):

| class | M4.5 (100) | M4.6 (150) | M4.8 (250) |
|---|---:|---:|---:|
| shirt | 0.099 | 0.348 | 0.298 |
| jacket | 0.358 | 0.440 | 0.530 |
| sweater | 0.000 | 0.031 | 0.000 |
| trousers | 0.505 | 0.586 | 0.704 |
| shorts | 0.465 | 0.554 | 0.503 |
| skirt | 0.127 | 0.220 | 0.210 |
| dress | 0.706 | 0.735 | 0.751 |
| jumpsuit | 0.057 | 0.038 | 0.105 |
| shoes | 0.528 | 0.608 | 0.623 |
| bag | 0.138 | 0.101 | 0.270 |
| hat | 0.190 | 0.252 | 0.443 |
| belt | 0.053 | 0.033 | 0.105 |
| scarf | 0.044 | 0.000 | 0.005 |
| watch | 0.000 | 0.000 | 0.215 |
| sunglasses | 0.216 | 0.372 | 0.485 |

### What improved vs what did not

- **Genuine detector change (not just a lower threshold):** jacket, dress, trousers, hat, and bag now have multiple true positives at 0.5. Watch and sunglasses have their first ≥0.5 hits on this slice (1 and 3). Mean IoU of those matches is higher than M4.6 (0.801 vs 0.770).
- **Still confidence-only:** shirt max score is 0.336; 17/27 shirts are correct below 0.5 and **zero** cross 0.5. Jumpsuit max is 0.397. Lowering the threshold is what surfaces them, and it also inflates skirt/bag false positives.
- **Small-object:** hat and bag improved at 0.5. Watch and belt barely did (1 TP each). Sunglasses are partly low-confidence (12 correct below 0.5, 11 missed).
- **Unchanged failure:** scarf AP stays ~0; boxes that exist do not match scarf ground truth (5 wrong class, 6 low IoU).
- **Precision cost:** overall precision is 0.738 vs M4.6’s 0.781 on a smaller slice. Skirt precision is 0.23 (41 FP).

## 11. Restrictions honored

- M4.6 `best_model.pth` left in place and used only as initialization.
- No production code, taxonomy, or label edits.
- No full-dataset training.
- Best checkpoint chosen by validation loss, not by the last epoch.
- Score 0.10 is reported only as a sweep point and is not the operating point.

**MILESTONE 4.8 STATUS: PASS**
