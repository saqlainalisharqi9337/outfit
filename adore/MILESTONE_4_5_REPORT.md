# Milestone 4.5 — Evaluate the 500-Image Class-Aware Mask R-CNN Run

**MILESTONE 4.5 STATUS: PASS**

Evaluation and analysis only. The best checkpoint was **not** overwritten. Full-dataset training was **not** started. FastAPI / YOLO / production inference / the 15-class taxonomy were **not** modified.

This is **not** a production-ready detector.

## 1. Training configuration

From `checkpoints/maskrcnn/history.json` (class-aware CPU run, 43.7 min):

| Setting | Value |
|---|---|
| train images | 500 |
| val images (during training) | 100 |
| epochs | 3 |
| subset | `class_aware` |
| batch size | 1 |
| lr | 0.005 |
| device | cpu |
| min_size / max_size | 256 / 320 |
| seed | 42 |
| stored eval score (config) | 0.3 |

| Epoch | train_loss | val_loss | checkpoint |
|---:|---:|---:|---|
| 1 | 1.788042 | 2.005305 | last only |
| 2 | 1.554349 | **1.753687** | **best_model.pth saved** |
| 3 | 1.426603 | 1.917990 | previous best kept |

Train loss fell all three epochs. Val loss improved at epoch 2 then rose at epoch 3 (mild overfit on the small subset). Best weights are epoch 2.

## 2. Best checkpoint

`checkpoints/maskrcnn/best_model.pth` (351,651,352 bytes, val_loss 1.753687). Reloaded successfully.

The first eval attempt used `checkpoints\maskrcnn\best_model.pth` from `ml_service` and failed (`Checkpoint not found`). The correct path is one directory up:

```text
.\.venv\Scripts\python.exe -m training.evaluate_maskrcnn --checkpoint ..\checkpoints\maskrcnn\best_model.pth --max-images 100
```

No evaluation-code change was required. The checkpoint was not rewritten.

## 3. M4.3 vs M4.5 comparison

| | M4.3 | M4.5 |
|---|---|---|
| train / val / epochs | 100 / 50 / 1, first-N JSON | 500 / 100 / 3, class-aware |
| eval images | 50 | 100 |
| score / IoU | 0.5 / 0.5 | **0.5 / 0.5** |
| predictions | **0** | **189** |
| precision | 0.00 (0.10 at score 0.05) | **0.556** |
| recall | 0.00 (0.39 at score 0.05) | **0.323** |
| mAP@50 | 0.043 | **0.232** |
| mAP@50:95 | 0.013 | **0.093** |
| mean IoU of TP | 0.00 at 0.5 | **0.740** |
| useful classes at 0.5 | none | shoes, dress, jacket, trousers, skirt, sunglasses |

**M4.5 improved the detector** at the same 0.5 operating point: from zero detections to 189, mAP@50 ×5.4, and usable precision. Recall at 0.5 (0.32) is still below M4.3’s *low-threshold* recall (0.39 at 0.05), which is expected: M4.5 is much more conservative and far less noisy.

## 4. Overall metrics (score 0.5, IoU 0.5, 100 val images)

| metric | value |
|---|---|
| validation images | 100 |
| predictions | 189 |
| ground-truth instances | 325 |
| confidence threshold | **0.5** |
| IoU threshold | **0.5** |
| precision | **0.5556** |
| recall | **0.3231** |
| mean IoU (TP) | 0.7395 |
| mAP@50 | **0.2324** |
| mAP@50:95 | 0.0934 |

## 5. Per-class metrics

At score 0.5 / IoU 0.5. AP@50 is ranking-based (uses all scored detections).

| class | n_gt | tp | fp | fn | P | R | AP50 |
|---|---:|---:|---:|---:|---:|---:|---:|
| shirt | 7 | 0 | 0 | 7 | 0.000 | 0.000 | 0.099 |
| jacket | 22 | 11 | 17 | 11 | 0.393 | 0.500 | 0.358 |
| sweater | 1 | 0 | 0 | 1 | 0.000 | 0.000 | 0.000 |
| trousers | 25 | 7 | 3 | 18 | 0.700 | 0.280 | 0.505 |
| shorts | 11 | 0 | 0 | 11 | 0.000 | 0.000 | 0.465 |
| skirt | 9 | 3 | 14 | 6 | 0.176 | 0.333 | 0.127 |
| dress | 45 | 9 | 2 | 36 | 0.818 | 0.200 | 0.706 |
| jumpsuit | 5 | 0 | 0 | 5 | 0.000 | 0.000 | 0.057 |
| shoes | 138 | 73 | 48 | 65 | 0.603 | 0.529 | 0.528 |
| bag | 14 | 0 | 0 | 14 | 0.000 | 0.000 | 0.138 |
| hat | 7 | 0 | 0 | 7 | 0.000 | 0.000 | 0.190 |
| belt | 19 | 0 | 0 | 19 | 0.000 | 0.000 | 0.053 |
| scarf | 5 | 0 | 0 | 5 | 0.000 | 0.000 | 0.044 |
| watch | 6 | 0 | 0 | 6 | 0.000 | 0.000 | 0.000 |
| sunglasses | 11 | 2 | 0 | 9 | 1.000 | 0.182 | 0.216 |

Strongest at 0.5: **dress** (P 0.82, AP 0.71), **shoes** (R 0.53, AP 0.53), **trousers** (P 0.70, AP 0.51), **jacket** (R 0.50). Shorts have AP 0.47 but **zero** TP at 0.5 (scores sit below the threshold). Still weak/absent at 0.5: shirt, sweater, jumpsuit, bag, hat, belt, scarf, watch.

## 6. Prediction quality

Eight overlays in `outputs/maskrcnn_preview/` (drawn at score ≥ 0.3 so mid-confidence boxes are visible).

- **Separate pieces:** yes, more than M4.3. Examples: jacket + two shoes (`pred_02`); jacket + trousers (`pred_06`); dress + shorts (`pred_07`); jacket + two boots (`pred_04`).
- **Masks:** jacket/dress masks often follow the garment; still ragged on shirts/open coats (`pred_00`, `pred_05`). Shoe masks are small but localized.
- **Duplicates:** still present (two `jacket` boxes on one open shirt in `pred_05`; overlapping `shoes` in `pred_02`). Much less of the M4.3 “dozens of 0.05 shoes” pattern.
- **Dress/jacket:** a mini-dress also got `shirt 0.35` (`pred_01`). Open shirt over shorts labeled `jacket` twice and `skirt` on the shorts (`pred_05`).
- **Trousers/shirt:** trousers on jeans in `pred_06` is a true separate instance. Shirt still mostly missing at 0.5 (0 TP).
- **Accessories:** bag, hat, belt, scarf, watch have 0 TP at 0.5. Sunglasses 2 TP / 11 GT. A door handle was still called `shoes 0.30` (`pred_00`).
- **Small objects:** watches undetected; sunglasses rare; belts undetected.
- **False positives:** 84 FP vs 105 TP at 0.5 (precision 0.56). Skirt FP is high (14 FP / 3 TP). Shoes still the largest FP count (48).

## 7. Error analysis

- Missed garments remain the main recall hole: 220 FN / 325 GT at 0.5, especially dress FN=36 and shoes FN=65 (pairs), plus almost all accessories.
- Dress is precise when it fires, but conservative (R 0.20).
- Skirt precision is poor (0.18) — shorts/skirts/dresses still leak into each other in previews.
- Shirt has no 0.5 detections; AP 0.10 says a weak ranked signal exists below threshold.
- Sweater/watch AP 0.00 in this 100-image val prefix (`n_gt` 1 and 6).
- False `shoes` on a door handle shows residual objectness noise, far less than M4.3 at 0.05.

Do **not** change the taxonomy from these errors.

## 8. Did the class-aware subset improve coverage?

**Yes, relative to M4.3’s first-100 prefix.**

M4.3 train slice was 139 shoes / 9 shirts / 1 sweater. This eval’s 100-val prefix still has 138 shoe GT (val eval is first-N, not class-aware), but the **trained** model now fires jacket, trousers, skirt, dress, shoes, and sunglasses at 0.5 — classes that produced nothing at 0.5 after the non-aware 100-image run.

Rare classes are still under-represented in this particular val prefix (sweater `n_gt=1`). That is an evaluation-slice issue, not proof the train subset lacked them.

## 9. Is additional training justified?

**Yes.** Losses were still falling on train; val was best at epoch 2. Metrics moved from unusable at 0.5 to a real (weak) detector. Remaining holes (shirt, bag, hat, belt, scarf, watch, jumpsuit) need more images/epochs, not a taxonomy rewrite and not FastAPI integration.

Not justified yet: full 37,887-image CPU training (would be tens of hours) or replacing YOLO.

## 10. Recommended next experiment

Keep the 15 classes. Do not overwrite `best_model.pth` except when val loss improves. Do not wire into FastAPI.

Suggested M4.6 (still capped, class-aware, CPU-safe):

```text
.\.venv\Scripts\python.exe -u training\train_maskrcnn.py --max-train-images 1000 --max-val-images 150 --epochs 5 --batch-size 1 --num-workers 0 --class-aware-subset --lr 0.005 --seed 42 --score-threshold 0.3 --resume ..\checkpoints\maskrcnn\best_model.pth --checkpoint-dir ..\checkpoints\maskrcnn
```

Then evaluate with `..\checkpoints\maskrcnn\best_model.pth` (not `checkpoints\...` from `ml_service`). Optional: class-aware val eval so sweater/jumpsuit/scarf are not left to the JSON prefix.

If a GPU becomes available, 2,000/200/8 at min_size 800 is the better next step than a 44k CPU pass.
