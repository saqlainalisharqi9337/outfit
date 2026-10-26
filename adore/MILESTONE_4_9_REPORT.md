# Milestone 4.9 — Final Validation and Robustness Testing

**MILESTONE 4.9 STATUS: PASS**

Evaluation only. `checkpoints/maskrcnn/m4_8/best_model.pth` was loaded and **not** modified. No training. FastAPI / YOLO / production gates / Flutter / the 15-class taxonomy / dataset labels / production inference were **not** modified. Mask R-CNN was **not** integrated into the app.

This result is **not** a production-readiness claim.

## 1. Objective

Measure the frozen M4.8 candidate on a fixed validation set larger than the M4.8 250-image slice, at confidence 0.50 / 0.40 / 0.30, and inspect prediction previews for the remaining weak classes.

## 2. Checkpoint

| field | value |
|---|---|
| path | `checkpoints/maskrcnn/m4_8/best_model.pth` |
| epoch | **2** |
| `best` | `True` |
| val_loss (training) | 1.283381533741951 |
| classes | 16 (background 0 + 15 foreground) |
| min_size / max_size | 320 / 480 (from the checkpoint config) |

## 3. Evaluation configuration

The converted validation split has **1146** images and **3800** ground-truth instances. That full split was used. It is the official labeled val JSON, first-N is the entire file because every usable val image was kept.

| setting | value |
|---|---|
| images | **1146** |
| device | cpu |
| inference time | **1515.8 s** (~1.32 s/image) |
| IoU | 0.5 |
| official scores | 0.50, 0.40, 0.30 |
| RPN | same CPU caps used by earlier eval (`apply_cpu_fast`) |

Artifact: `checkpoints/maskrcnn/m4_9/threshold_study.json`.

**Two AP definitions** (same distinction as M4.7/M4.8):

- **Ranking mAP** uses all model detections. This is the number comparable to the M4.5 / M4.6 / M4.8 headline mAP.
- **Filtered mAP** in the threshold table uses only detections at or above that score. It is lower and is not the headline AP.

Ranking result on these 1146 images: **mAP@50 = 0.3260**, **mAP@50:95 = 0.1741**, 10031 raw predictions.

Score 0.10 was computed by the existing sweep and is **not** recommended (precision 0.368, 4109 FP).

## 4. Threshold results

IoU = 0.5. Ground truth is 3800 at every row. mAP columns are **filtered**.

| score | n_pred | n_gt | TP | FP | FN | P | R | mAP@50 (filtered) | mAP@50:95 (filtered) | mean IoU TP |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.50 | 2181 | 3800 | 1561 | 620 | 2239 | **0.716** | **0.411** | 0.210 | 0.117 | **0.802** |
| 0.40 | 2676 | 3800 | 1769 | 907 | 2031 | 0.661 | 0.466 | 0.236 | 0.131 | 0.797 |
| 0.30 | 3292 | 3800 | 1935 | 1357 | 1865 | 0.588 | 0.509 | 0.259 | 0.142 | 0.792 |

Mean IoU of true positives stays about 0.79–0.80. Lowering the score raises recall and adds false positives. 0.50 remains the reporting operating point.

## 5. Per-class results at score 0.5 / IoU 0.5

AP50 in this table is **ranking AP** (all detections), so it can be non-zero when TP at 0.5 is 0. Filtered AP50 at score 0.5 is 0.000 for shirt, sweater, jumpsuit, and scarf.

| class | n_gt | TP | FP | FN | P | R | ranking AP50 |
|---|---:|---:|---:|---:|---:|---:|---:|
| shirt | 102 | 0 | 0 | 102 | 0.000 | 0.000 | 0.184 |
| jacket | 287 | 105 | 37 | 182 | 0.739 | 0.366 | 0.542 |
| sweater | 21 | 0 | 0 | 21 | 0.000 | 0.000 | 0.018 |
| trousers | 314 | 180 | 65 | 134 | 0.735 | 0.573 | 0.630 |
| shorts | 106 | 17 | 2 | 89 | 0.895 | 0.160 | 0.372 |
| skirt | 162 | 78 | 159 | 84 | 0.329 | 0.481 | 0.325 |
| dress | 508 | 350 | 156 | 158 | 0.692 | 0.689 | 0.741 |
| jumpsuit | 21 | 0 | 0 | 21 | 0.000 | 0.000 | 0.095 |
| shoes | 1565 | 706 | 69 | 859 | 0.911 | 0.451 | 0.606 |
| bag | 214 | 43 | 88 | 171 | 0.328 | 0.201 | 0.157 |
| hat | 74 | 43 | 30 | 31 | 0.589 | 0.581 | 0.518 |
| belt | 164 | 5 | 7 | 159 | 0.417 | 0.030 | 0.082 |
| scarf | 48 | 0 | 0 | 48 | 0.000 | 0.000 | 0.009 |
| watch | 84 | 5 | 6 | 79 | 0.455 | 0.060 | 0.108 |
| sunglasses | 130 | 29 | 1 | 101 | 0.967 | 0.223 | 0.505 |

Shirt maximum score on this set is **0.339** (586 predictions, **0** at or above 0.5). Scarf maximum is **0.141** (421 predictions, **0** at or above 0.5). Sweater max 0.414. Jumpsuit max 0.439.

## 6. Error categories

Counts are the best overlapping detection per ground-truth box (IoU 0.5). “Low-conf” means the correct class with score below 0.5.

| class | ≥0.5 correct | <0.5 correct | wrong class | IoU&lt;0.5 | missed |
|---|---:|---:|---:|---:|---:|
| shirt | 0 | 61 | 10 | 23 | 8 |
| jacket | 104 | 130 | 26 | 26 | 1 |
| sweater | 0 | 3 | 13 | 5 | 0 |
| trousers | 179 | 59 | 21 | 41 | 14 |
| shorts | 17 | 42 | 13 | 27 | 7 |
| skirt | 78 | 56 | 10 | 12 | 6 |
| dress | 350 | 120 | 18 | 17 | 3 |
| jumpsuit | 0 | 16 | 3 | 2 | 0 |
| shoes | 705 | 351 | 8 | 225 | 276 |
| bag | 43 | 49 | 16 | 82 | 24 |
| hat | 43 | 5 | 1 | 6 | 19 |
| belt | 5 | 42 | 8 | 55 | 54 |
| scarf | 0 | 10 | 13 | 21 | 4 |
| watch | 5 | 20 | 5 | 11 | 43 |
| sunglasses | 29 | 42 | 1 | 12 | 46 |

Mapped to the requested categories, using these counts plus the previews:

| code | category | evidence |
|---|---|---|
| A | missed detection | watch 43/84, sunglasses 46/130, belt 54/164, shoes 276/1565 have no overlapping box |
| B | low-confidence correct | shirt 61/102 correct below 0.5 and **none** at 0.5; jumpsuit 16/21; jacket still has 130 correct below 0.5 |
| C | wrong class | sweater 13/21; scarf 13/48; shorts→skirt = 7 at IoU 0.5. Preview: pink shirt labeled `dress 0.39`; patterned shorts labeled `skirt 0.64` |
| D | poor localization | bag 82/214 and belt 55/164 overlap below 0.5 |
| E | poor mask | jacket mask covers the pink shirt; skirt mask has holes; jacket mask paints the fur piece while the box is the blazer |
| F | duplicate detection | three `shoes` boxes on one pair; two overlapping `skirt` boxes plus a `bag` on one dress |
| G | background false positive | these eight previews do not show a background object (door, floor, crowd) labeled as clothing. Skirt’s 159 FP are extra clothing boxes, not a counted background class |
| H | small-object failure | watch 5/84 TP and 43 missed; belt 5/164 TP; scarf never reaches 0.5 |

Focused wrong-class pairs at IoU ≥ 0.5: shorts→skirt 7, jacket→shirt 3, shirt→dress 1, dress→shirt 1, trousers→shirt 1, bag→belt 1, hat→bag 1, scarf→belt 1, watch→belt 1.

## 7. Preview observations

Twelve overlays at score ≥ 0.3 in `outputs/maskrcnn_m4_9/` (eight unique photos; the first photo contains shirt, jacket, belt, and sunglasses ground truth).

- **Separate pieces that match:** `jacket 0.75` on the blazer; `dress 0.70` on the runway dress; `hat 0.83`; `skirt 0.83` on the purple skirt; `trousers 0.96` and `shoes 0.93` on the tan suit; two separate `shoes` boxes on the two sneakers.
- **Missed:** open shirt is not labeled shirt; plaid overshirt, shorts, and glasses on the bridge photo are missed (only `shoes 0.32`); belt and fur scarf are not boxed; wristwatch is not boxed.
- **Wrong class / overlap:** shirt called `dress 0.39`; shorts called `skirt 0.64`; top called both `jacket 0.48` and `dress 0.44`; jumpsuit/dress split into `dress 0.88` plus two `skirt` boxes and a `bag 0.47`.
- **Duplicates:** three shoe boxes on one pair of heels.
- **Masks:** blazer mask leaks onto the shirt; skirt mask is patchy; jacket mask covers the fur accessory.
- **Similar silhouettes:** shorts vs skirt, and dress vs jacket-over-top, are the visible confusions. Multi-color garments (plaid, cartoon print) are partly missed or given a second class.
- **Occlusion:** the seated pose misses the upper garment and one boot; the arm on the door does not create a door-handle false positive in that preview.

## 8. Comparison

Val loss is not compared here. Detection numbers use score 0.5 and IoU 0.5. **Validation image counts differ**, so M4.5 / M4.6 / M4.8 / M4.9 are **not** a paired test. mAP below is **ranking** mAP.

| | M4.5 | M4.6 | M4.8 | M4.9 |
|---|---:|---:|---:|---:|
| training images | 500 | 1000 | 2000 | none (frozen M4.8) |
| best epoch | 2 | 1 | 2 | 2 (same checkpoint) |
| validation images | 100 | 150 | 250 | **1146** |
| precision | 0.556 | 0.781 | 0.738 | **0.716** |
| recall | 0.323 | 0.316 | 0.414 | **0.411** |
| mAP@50 | 0.232 | 0.288 | 0.350 | **0.326** |
| mAP@50:95 | 0.093 | 0.146 | 0.192 | **0.174** |
| mean IoU (TP) | 0.740 | 0.770 | 0.801 | **0.802** |

M4.9 precision and recall stay close to the M4.8 250-image operating point (0.738 / 0.414 vs 0.716 / 0.411). Ranking mAP is lower than the M4.8 slice (0.326 vs 0.350). That drop is on a larger set; it is not evidence the checkpoint changed.

## 9. Remaining limitations

- Shirt: 0 TP at 0.5 on all 1146 images. Highest score 0.339.
- Scarf: 0 TP at 0.5. Highest score 0.141. Ranking AP50 0.009.
- Belt: 5/164 TP. Watch: 5/84 TP, 43 missed.
- Sweater and jumpsuit: 0 TP at 0.5 (21 GT each).
- Skirt: 159 FP against 78 TP at 0.5.
- Shoes are precise (0.911) but 859 of 1565 are still false negatives.
- Matched boxes overlap well (mean IoU 0.802). The gap is missed and low-score instances, not IoU of the matches.

## 10. Integration recommendation

**Do not start integration testing with this checkpoint.**

Run another targeted training experiment first. The full validation set still shows shirt and scarf with no detection at 0.5, belt and watch mostly missed, and skirt false positives. Jacket, dress, trousers, hat, and shoes are the classes with usable precision at 0.5, which is not enough to treat the 15-class detector as ready to wire into FastAPI or Flutter.

**MILESTONE 4.9 STATUS: PASS**
