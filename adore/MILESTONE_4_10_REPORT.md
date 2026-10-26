# Milestone 4.10 — Targeted Weak-Class Mask R-CNN Training Experiment

**MILESTONE 4.10 STATUS: PASS**

Training and evaluation only. `checkpoints/maskrcnn/m4_8/best_model.pth` was used as initialization and was **not** overwritten (SHA-256 still `DA085001D539FE5FD80B64FA73C312E41D7436DE314EE1C4354FA145B5D6CBD8`). FastAPI / YOLO / production gates / Flutter / the recommendation system / the 15-class taxonomy / dataset labels were **not** modified. Mask R-CNN was **not** integrated into the app.

This is **not** a production-ready detector. Completing the experiment is not the same as a clean accuracy win.

## 1. Objective

Train a new checkpoint from the frozen M4.8 weights on a larger share of shirt, scarf, belt, watch, and skirt images, while keeping jacket, dress, trousers, and shoes in the same run.

## 2. M4.9 baseline

Same checkpoint family, full validation set (1,146 images, 3,800 GT), score 0.5, IoU 0.5:

| metric | M4.9 |
|---|---:|
| precision | 0.716 |
| recall | 0.411 |
| ranking mAP@50 | 0.326 |
| ranking mAP@50:95 | 0.174 |
| mean IoU | 0.802 |

At 0.5: shirt 0/102 TP (max score 0.339), scarf 0/48 TP (max 0.141), belt 5/164 TP, watch 5/84 TP, skirt 78 TP and 159 FP.

## 3. Preprocessing audit

The dataset loader does **not** resize. It reads the RGB file, checks that the pixel size matches the COCO JSON, and returns the image at native resolution. Resize happens inside torchvision `GeneralizedRCNNTransform` when the model runs.

Measured on all **37,887** training images (`checkpoints/maskrcnn/m4_10/preprocess_audit.json`):

| item | value |
|---|---|
| original width | min 232, median 682, max 1024 |
| original height | min 388, median 1024, max 1024 |
| model `min_size` / `max_size` | 320 / 480 (unchanged from M4.8) |
| aspect ratio | preserved. Scale is `min(320 / short_side, 480 / long_side)` |
| resized before the model | **no** |
| masks resized | **yes**, inside the model, with the same scale as the image |
| random horizontal flip | **no** |
| other augmentation | **no** |
| boxes with shorter side under 32 px before resize | 10,408 / 115,215 |
| boxes with shorter side under 16 px after the 320/480 scale | **13,262 / 115,215** |

Small objects can get smaller. The long side is capped at 480, so a wide photo is scaled down and a watch or belt that was already small can fall below 16 px. Preprocessing was **not** changed in this milestone.

## 4. Targeted subset

New selector `weak_class_select` in `ml_service/training/dataset.py`. It does not copy images, does not edit labels, and does not invent boxes.

- 72% of the training slots are filled by round-robin over images that contain shirt, scarf, belt, watch, or skirt.
- The remaining slots are round-robin over the other 10 classes, so shoes, dress, trousers, and jacket stay in the run.
- Each image is used at most once.
- Validation during training stays ordinary class-aware sampling (250 images), not the weak-class rule.

## 5. Exact class distribution

2,300 training images. Counts are instances, not images. Source: `checkpoints/maskrcnn/m4_10/subset_stats.json`.

| class | M4.8 train (2,000 images) | M4.10 train (2,300 images) |
|---|---:|---:|
| shirt | 443 | **655** |
| scarf | 196 | **383** |
| belt | 458 | **681** |
| watch | 331 | **526** |
| skirt | 279 | **508** |
| jacket | 660 | 780 |
| sweater | 180 | 124 |
| trousers | 732 | 859 |
| shorts | 229 | 179 |
| dress | 445 | 475 |
| jumpsuit | 161 | 95 |
| shoes | 2424 | 2701 |
| bag | 558 | 570 |
| hat | 294 | 266 |
| sunglasses | 445 | 455 |

Shoes (2,701), trousers (859), jacket (780), and dress (475) are still present.

## 6. Training configuration

```text
.\.venv_m48\Scripts\python.exe -u training\train_maskrcnn.py --max-train-images 2300 --max-val-images 250 --epochs 3 --batch-size 1 --num-workers 0 --weak-class-subset --score-threshold 0.5 --checkpoint-dir ..\checkpoints\maskrcnn\m4_10 --init-from ..\checkpoints\maskrcnn\m4_8\best_model.pth --min-size 320 --max-size 480 --print-every 100 --device cpu
```

| setting | value |
|---|---|
| initialization | `checkpoints/maskrcnn/m4_8/best_model.pth` (epoch 2, val_loss 1.283382) |
| COCO start | not used |
| optimizer | new |
| epoch counter | restarted at 1 |
| device | cpu |
| batch / workers | 1 / 0 |
| lr / weight decay | 0.005 / 0.0005 |
| epochs | 3 |
| skipped steps | 0 |
| output | `checkpoints/maskrcnn/m4_10/` |

Load succeeded before epoch 1: `source_epoch=2`, `source_best=True`.

## 7. Losses

Training validation loss is on the 250-image class-aware subset. It is **not** comparable to M4.8’s validation loss.

| epoch | train_loss | val_loss | elapsed_seconds | checkpoint |
|---:|---:|---:|---:|---|
| 1 | 1.316505 | 1.316078 | 11379.6 | best at the time |
| 2 | 1.249863 | 1.362044 | 6835.6 | previous best kept |
| 3 | 1.219508 | **1.037064** | 17504.2 | **best_model.pth** |

Total recorded time: 35,722 s. Train loss fell each epoch. Val loss rose at epoch 2 and fell at epoch 3.

## 8. Best epoch

**Epoch 3.** `best_model.pth` has `best=True` and val_loss 1.037064. `last_model.pth` is the same epoch because epoch 3 was best.

## 9. Evaluation

Best checkpoint only. **Same 1,146 validation images and 3,800 GT as M4.9.** CPU, 1,769 s. IoU 0.5.

Ranking mAP (all detections, same rule as M4.6–M4.9): **mAP@50 = 0.3177**, **mAP@50:95 = 0.1780**, 9,836 raw predictions.

Operating points. The mAP columns here are **filtered** (detections at or above that score). They are not the ranking mAP above.

| score | n_pred | n_gt | TP | FP | FN | P | R | mAP@50 (filtered) | mAP@50:95 (filtered) | mean IoU |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.50 | 2574 | 3800 | 1810 | 764 | 1990 | **0.703** | **0.476** | 0.237 | 0.139 | **0.803** |
| 0.40 | 3015 | 3800 | 1932 | 1083 | 1868 | 0.641 | 0.508 | 0.255 | 0.148 | 0.801 |
| 0.30 | 3623 | 3800 | 2064 | 1559 | 1736 | 0.570 | 0.543 | 0.274 | 0.157 | 0.798 |

Score 0.10 was computed and is **not** recommended (precision 0.355, 4,355 FP).

## 10. Per-class at score 0.5

AP50 is **ranking** AP50. Recall is the 0.5 operating point.

| class | n_gt | TP | FP | FN | P | R | ranking AP50 |
|---|---:|---:|---:|---:|---:|---:|---:|
| shirt | 102 | 5 | 5 | 97 | 0.500 | 0.049 | 0.145 |
| jacket | 287 | 159 | 106 | 128 | 0.600 | 0.554 | 0.548 |
| sweater | 21 | 0 | 0 | 21 | 0.000 | 0.000 | 0.015 |
| trousers | 314 | 183 | 82 | 131 | 0.691 | 0.583 | 0.596 |
| shorts | 106 | 17 | 1 | 89 | 0.944 | 0.160 | 0.330 |
| skirt | 162 | 58 | 87 | 104 | 0.400 | 0.358 | 0.299 |
| dress | 508 | 276 | 68 | 232 | 0.802 | 0.543 | 0.719 |
| jumpsuit | 21 | 0 | 0 | 21 | 0.000 | 0.000 | 0.014 |
| shoes | 1565 | 944 | 240 | 621 | 0.797 | 0.603 | 0.621 |
| bag | 214 | 25 | 43 | 189 | 0.368 | 0.117 | 0.130 |
| hat | 74 | 21 | 5 | 53 | 0.808 | 0.284 | 0.397 |
| belt | 164 | 16 | 29 | 148 | 0.356 | 0.098 | 0.084 |
| scarf | 48 | 1 | 5 | 47 | 0.167 | 0.021 | 0.052 |
| watch | 84 | 21 | 75 | 63 | 0.219 | 0.250 | 0.141 |
| sunglasses | 130 | 84 | 18 | 46 | 0.824 | 0.646 | 0.675 |

Max confidence on this set: shirt **0.690**, scarf **0.700**, belt **0.887**, watch **0.953**. M4.9 maxima were 0.339, 0.141, 0.623, and 0.795.

## 11. Small-object analysis

Paired with M4.9 on the same 1,146 images, score 0.5.

| class | M4.9 TP / n_gt | M4.10 TP / n_gt | M4.9 recall | M4.10 recall | M4.9 AP50 | M4.10 AP50 | M4.10 max score |
|---|---:|---:|---:|---:|---:|---:|---:|
| watch | 5/84 | 21/84 | 0.060 | 0.250 | 0.108 | 0.141 | 0.953 |
| belt | 5/164 | 16/164 | 0.030 | 0.098 | 0.082 | 0.084 | 0.887 |
| scarf | 0/48 | 1/48 | 0.000 | 0.021 | 0.009 | 0.052 | 0.700 |
| sunglasses | 29/130 | 84/130 | 0.223 | 0.646 | 0.505 | 0.675 | 0.993 |
| hat | 43/74 | 21/74 | 0.581 | 0.284 | 0.518 | 0.397 | 0.959 |
| bag | 43/214 | 25/214 | 0.201 | 0.117 | 0.157 | 0.130 | 0.975 |

Sampling did **not** solve small objects. Watch and belt recall rose, but watch precision fell from 0.455 to 0.219 (75 FP). Scarf gained one true positive. Hat and bag got worse. 39/84 watches and 65/164 belts are still complete misses. 13,262 boxes are under 16 px after the current resize, which this run did not change.

## 12. Skirt false positives

| | M4.9 | M4.10 |
|---|---:|---:|
| TP | 78 | 58 |
| FP | 159 | 87 |
| precision | 0.329 | 0.400 |
| recall | 0.481 | 0.358 |

Precision improved because false positives fell faster than true positives. Recall fell.

GT boxes matched to a different class at IoU ≥ 0.5: **shorts→skirt = 2** (M4.9 was 7). Dress→shirt = 3, jacket→shirt = 1. That pair count does **not** explain 87 skirt false positives. Most skirt false positives are extra skirt boxes that are not a shorts ground-truth match.

Preview evidence, not a full cause:

- `skirt_0013`: the purple skirt is `skirt 0.52`. The cartoon top is `jacket 0.64`, not a second skirt. Shoes are separate. The background person is not labeled.
- `watch_0028`: the purple skirt is `skirt 0.45` under a `dress 0.53` / `jacket 0.61` overlap. That is a duplicate garment label, not a background object.
- `hat_0007`: patterned shorts are labeled `bag`, not skirt, at score ≥ 0.3. The red hat is missed.

No taxonomy change and no skirt gate were added.

## 13. Preview observations

Seven unique overlays at score ≥ 0.3 in `outputs/maskrcnn_m4_10/`.

- **Correct:** `shirt 0.47` on the pink shirt (M4.9 called this `dress 0.39`); `sunglasses 0.80`; `jacket 0.88`; `skirt 0.52`; separate `shoes` on both sneakers; `dress 0.88`; `jacket 0.80`, `trousers 0.95`, `belt 0.32`, `shoes 0.98`.
- **Low confidence:** shirt 0.47 and skirt 0.45 are below 0.5. Belt on the tan suit is 0.36.
- **Wrong or overlapping class:** jacket box covers the shirt and the arm; dress and jacket overlap the same bodice on the runway skirt; two `bag` boxes sit on the torso and a small green bag while the hat and shorts are missed.
- **Missed:** fur scarf is not labeled scarf (the jacket mask covers it); wristwatch on the runway model is not boxed; red hat is not boxed.
- **Duplicates:** two shoe boxes on one pair of heels (`shoes 0.65` and `0.97`).
- **Masks:** jacket mask spills across the pink shirt and the extended arm; skirt mask on the cartoon outfit covers only part of the skirt; jacket mask on the fur look paints the fur, not a separate scarf.
- **Background:** the door handle and the person on the grass are not given clothing labels in these previews.

## 14. Comparison

mAP is ranking mAP. Score 0.5, IoU 0.5. **M4.9 and M4.10 use the same 1,146 images.** M4.5 (100), M4.6 (150), and M4.8 (250) are smaller prefixes and are not paired with them.

| | M4.5 | M4.6 | M4.8 | M4.9 | M4.10 |
|---|---:|---:|---:|---:|---:|
| training images | 500 | 1000 | 2000 | none | 2300 |
| best epoch | 2 | 1 | 2 | 2 (frozen M4.8) | **3** |
| validation images | 100 | 150 | 250 | **1146** | **1146** |
| precision | 0.556 | 0.781 | 0.738 | 0.716 | 0.703 |
| recall | 0.323 | 0.316 | 0.414 | 0.411 | **0.476** |
| mAP@50 | 0.232 | 0.288 | 0.350 | 0.326 | 0.318 |
| mAP@50:95 | 0.093 | 0.146 | 0.192 | 0.174 | 0.178 |
| mean IoU | 0.740 | 0.770 | 0.801 | 0.802 | 0.803 |

Paired M4.9 → M4.10 on 1,146 images:

| class | M4.9 AP50 | M4.10 AP50 | M4.9 recall@0.5 | M4.10 recall@0.5 |
|---|---:|---:|---:|---:|
| shirt | 0.184 | 0.145 | 0.000 | 0.049 |
| scarf | 0.009 | 0.052 | 0.000 | 0.021 |
| belt | 0.082 | 0.084 | 0.030 | 0.098 |
| watch | 0.108 | 0.141 | 0.060 | 0.250 |
| skirt precision | 0.329 | **0.400** | 0.481 | 0.358 |
| jacket | 0.542 | 0.548 | 0.366 | 0.554 |
| dress | 0.741 | 0.719 | 0.689 | 0.543 |
| trousers | 0.630 | 0.596 | 0.573 | 0.583 |
| shoes | 0.606 | 0.621 | 0.451 | 0.603 |

## 15. Remaining limitations

- Shirt ranking AP fell (0.184 → 0.145) even though 5 boxes now clear 0.5. 61/102 shirts are still correct only below 0.5.
- Scarf is still 1/48 at 0.5.
- Watch recall rose and precision collapsed (75 FP).
- Hat recall fell from 0.581 to 0.284. Bag recall fell from 0.201 to 0.117.
- Dress recall fell from 0.689 to 0.543. Shoes precision fell from 0.911 to 0.797. Jacket and trousers did not collapse.
- Sweater and jumpsuit still have 0 TP at 0.5.
- The 320/480 resize still shrinks small boxes. This run did not change that.

## 16. Recommendation

Do **not** integrate this checkpoint.

The weak-class sample produced a **mixed** result, not a clean improvement. Shirt, scarf, belt, and watch now have a few detections above 0.5, and skirt precision rose, but hat and bag regressed, dress recall dropped, and watch false positives jumped. Another round of the same sampling, at the same 320/480 size, is not justified.

The next experiment should change the input scale (the audit shows 13,262 boxes under 16 px after resize), not only which images are sampled. Keep M4.8 and M4.10 checkpoints frozen.

**MILESTONE 4.10 STATUS: PASS**
